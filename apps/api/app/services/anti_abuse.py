from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, TooManyRequestsError
from app.models import AdminActionLog, IntegrityEvent, Issue, SupportTicket, SwipeFeedback, User
from app.models.enums import (
    AbuseRiskLevel,
    IntegrityEventSeverity,
    IssueStatus,
    ModerationResultStatus,
    SwipeDirection,
)
from app.schemas.issue import IssueCreate
from app.services.intelligence_utils import clamp, saturating_ratio

EVENT_ISSUE_SUBMISSION_CREATED = "issue_submission_created"
EVENT_ISSUE_SUBMISSION_RATE_LIMITED = "issue_submission_rate_limited"
EVENT_DUPLICATE_SUBMISSION_ATTEMPT = "duplicate_submission_attempt"
EVENT_FEEDBACK_ACTION = "feedback_action"
EVENT_FEEDBACK_RATE_LIMITED = "feedback_rate_limited"
EVENT_FEEDBACK_PATTERN_WARNING = "feedback_pattern_warning"
EVENT_SELF_SUPPORT_BLOCKED = "self_support_blocked"
EVENT_SUPPORT_EXISTING_ACTION = "support_existing_action"
EVENT_TICKET_CREATED = "ticket_created"
EVENT_TICKET_RATE_LIMITED = "ticket_rate_limited"
EVENT_REWRITE_REQUEST = "rewrite_request"
EVENT_REWRITE_RATE_LIMITED = "rewrite_rate_limited"
EVENT_MODERATION_APPROVED = "moderation_approved"
EVENT_MODERATION_REJECTED = "moderation_rejected"
EVENT_MODERATION_REVIEW = "moderation_manual_review"

SANCTION_ACTION_KEYWORDS = (
    "warn",
    "suspend",
    "ban",
    "sanction",
    "deactivate",
    "restrict",
)


@dataclass(frozen=True)
class AntiAbuseConfig:
    assessment_window_days: int = 30
    issue_submission_window_minutes: int = 30
    issue_submission_limit: int = 4
    rejection_cooldown_window_hours: int = 24
    rejection_cooldown_limit: int = 3
    duplicate_attempt_window_days: int = 14
    duplicate_attempt_limit: int = 2
    feedback_window_seconds: int = 90
    feedback_limit: int = 18
    same_author_support_window_minutes: int = 20
    same_author_support_limit: int = 6
    ticket_window_minutes: int = 60
    ticket_limit: int = 3
    rewrite_window_minutes: int = 10
    rewrite_limit: int = 6
    medium_risk_threshold: float = 25.0
    high_risk_threshold: float = 60.0


@dataclass(frozen=True)
class AntiAbuseAssessment:
    risk_level: AbuseRiskLevel
    risk_score: float
    summary: str
    reasons: tuple[dict[str, Any], ...] = ()
    recommended_actions: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)


class AntiAbuseService:
    """Record and evaluate integrity-risk signals around user behavior.

    The service intentionally combines hard controls for obvious bursts with
    softer audit events for medium-risk behavior. That keeps the platform
    defensive without turning normal civic participation into a hostile flow.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        config: AntiAbuseConfig | None = None,
    ) -> None:
        self.session = session
        self.config = config or AntiAbuseConfig()

    async def assess_user(self, user_id: UUID) -> AntiAbuseAssessment:
        now = datetime.now(UTC)
        window_start = now - timedelta(days=self.config.assessment_window_days)
        recent_event_counts = await self._count_recent_event_types(user_id, since=window_start)
        recent_severity_counts = await self._count_recent_event_severities(
            user_id,
            since=window_start,
        )
        rejected_issue_count = int(
            await self.session.scalar(
                select(func.count(Issue.id)).where(
                    Issue.author_id == user_id,
                    Issue.status == IssueStatus.REJECTED,
                    Issue.created_at >= window_start,
                )
            )
            or 0
        )
        less_like_this_count = int(
            await self.session.scalar(
                select(func.count(SwipeFeedback.id))
                .join(Issue, SwipeFeedback.issue_id == Issue.id)
                .where(
                    Issue.author_id == user_id,
                    SwipeFeedback.direction == SwipeDirection.LESS_LIKE_THIS,
                    SwipeFeedback.updated_at >= window_start,
                )
            )
            or 0
        )
        sanction_count = await self._count_admin_sanctions(user_id)

        duplicate_attempt_signal = saturating_ratio(
            recent_event_counts.get(EVENT_DUPLICATE_SUBMISSION_ATTEMPT, 0),
            float(self.config.duplicate_attempt_limit + 1),
        )
        submission_cooldown_signal = saturating_ratio(
            recent_event_counts.get(EVENT_ISSUE_SUBMISSION_RATE_LIMITED, 0),
            1.0,
        )
        feedback_burst_signal = saturating_ratio(
            recent_event_counts.get(EVENT_FEEDBACK_RATE_LIMITED, 0)
            + recent_event_counts.get(EVENT_FEEDBACK_PATTERN_WARNING, 0),
            4.0,
        )
        low_quality_submission_signal = clamp(
            saturating_ratio(rejected_issue_count, float(self.config.rejection_cooldown_limit))
            * 0.7
            + saturating_ratio(less_like_this_count, 8.0) * 0.3
        )
        severity_signal = clamp(
            saturating_ratio(recent_severity_counts.get(IntegrityEventSeverity.HIGH, 0), 3.0)
            * 0.65
            + saturating_ratio(
                recent_severity_counts.get(IntegrityEventSeverity.MEDIUM, 0),
                5.0,
            )
            * 0.35
        )
        sanction_signal = saturating_ratio(sanction_count, 3.0)

        weighted_score = clamp(
            duplicate_attempt_signal * 0.22
            + submission_cooldown_signal * 0.24
            + feedback_burst_signal * 0.18
            + low_quality_submission_signal * 0.16
            + severity_signal * 0.12
            + sanction_signal * 0.08
        )
        risk_score = round(weighted_score * 100, 1)

        reasons: list[dict[str, Any]] = []
        if duplicate_attempt_signal >= 0.25:
            reasons.append(
                self._build_factor(
                    name="duplicate_attempts",
                    label="Repeated near-duplicate submissions",
                    signal=duplicate_attempt_signal,
                    points=round(duplicate_attempt_signal * 24, 2),
                    details={
                        "count": recent_event_counts.get(EVENT_DUPLICATE_SUBMISSION_ATTEMPT, 0),
                        "window_days": self.config.duplicate_attempt_window_days,
                    },
                )
            )
        if submission_cooldown_signal >= 0.25:
            reasons.append(
                self._build_factor(
                    name="submission_cooldown",
                    label="Submission cooldowns triggered",
                    signal=submission_cooldown_signal,
                    points=round(submission_cooldown_signal * 24, 2),
                    details={
                        "submission_rate_limits": recent_event_counts.get(
                            EVENT_ISSUE_SUBMISSION_RATE_LIMITED,
                            0,
                        ),
                    },
                )
            )
        if feedback_burst_signal >= 0.25:
            reasons.append(
                self._build_factor(
                    name="feedback_bursts",
                    label="Rapid feedback or support patterns",
                    signal=feedback_burst_signal,
                    points=round(feedback_burst_signal * 22, 2),
                    details={
                        "rate_limit_events": recent_event_counts.get(
                            EVENT_FEEDBACK_RATE_LIMITED,
                            0,
                        ),
                        "pattern_warnings": recent_event_counts.get(
                            EVENT_FEEDBACK_PATTERN_WARNING,
                            0,
                        ),
                    },
                )
            )
        if low_quality_submission_signal >= 0.25:
            reasons.append(
                self._build_factor(
                    name="low_quality_submissions",
                    label="Recent low-signal or rejected reporting",
                    signal=low_quality_submission_signal,
                    points=round(low_quality_submission_signal * 20, 2),
                    details={
                        "rejected_issues": rejected_issue_count,
                        "less_like_this_received": less_like_this_count,
                    },
                )
            )
        if severity_signal >= 0.25:
            reasons.append(
                self._build_factor(
                    name="high_severity_events",
                    label="Recent abuse-control events",
                    signal=severity_signal,
                    points=round(severity_signal * 20, 2),
                    details={
                        "high_events": recent_severity_counts.get(IntegrityEventSeverity.HIGH, 0),
                        "medium_events": recent_severity_counts.get(
                            IntegrityEventSeverity.MEDIUM,
                            0,
                        ),
                    },
                )
            )
        if sanction_signal >= 0.2:
            reasons.append(
                self._build_factor(
                    name="admin_sanctions",
                    label="Admin sanction history",
                    signal=sanction_signal,
                    points=round(sanction_signal * 14, 2),
                    details={"sanction_count": sanction_count},
                )
            )

        risk_level = AbuseRiskLevel.LOW
        if risk_score >= self.config.high_risk_threshold:
            risk_level = AbuseRiskLevel.HIGH
        elif risk_score >= self.config.medium_risk_threshold:
            risk_level = AbuseRiskLevel.MEDIUM

        recommended_actions = self._recommended_actions(risk_level)
        summary = self._summary_for_level(risk_level, reasons)
        metrics = {
            "recent_event_counts": recent_event_counts,
            "recent_severity_counts": {
                severity.value: count for severity, count in recent_severity_counts.items()
            },
            "rejected_issue_count": rejected_issue_count,
            "less_like_this_count": less_like_this_count,
            "sanction_count": sanction_count,
        }

        return AntiAbuseAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            summary=summary,
            reasons=tuple(reasons),
            recommended_actions=recommended_actions,
            metrics=metrics,
        )

    async def guard_issue_submission(
        self,
        *,
        user: User,
        payload: IssueCreate,
    ):
        now = datetime.now(UTC)
        submission_cutoff = now - timedelta(
            minutes=self.config.issue_submission_window_minutes
        )
        rejection_cutoff = now - timedelta(
            hours=self.config.rejection_cooldown_window_hours
        )
        duplicate_cutoff = now - timedelta(days=self.config.duplicate_attempt_window_days)

        recent_submission_count = int(
            await self.session.scalar(
                select(func.count(Issue.id)).where(
                    Issue.author_id == user.id,
                    Issue.created_at >= submission_cutoff,
                )
            )
            or 0
        )
        recent_rejection_count = int(
            await self.session.scalar(
                select(func.count(Issue.id)).where(
                    Issue.author_id == user.id,
                    Issue.status == IssueStatus.REJECTED,
                    Issue.created_at >= rejection_cutoff,
                )
            )
            or 0
        )

        if recent_submission_count >= self.config.issue_submission_limit:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_ISSUE_SUBMISSION_RATE_LIMITED,
                severity=IntegrityEventSeverity.HIGH,
                summary="Issue submission cooldown triggered by rapid reporting volume.",
                payload={
                    "recent_submission_count": recent_submission_count,
                    "window_minutes": self.config.issue_submission_window_minutes,
                },
                commit=True,
            )
            raise TooManyRequestsError(
                (
                    "You are submitting issues too quickly. Please wait before "
                    "creating another report."
                ),
                details={"retry_after_minutes": self.config.issue_submission_window_minutes},
            )

        if recent_rejection_count >= self.config.rejection_cooldown_limit:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_ISSUE_SUBMISSION_RATE_LIMITED,
                severity=IntegrityEventSeverity.HIGH,
                summary="Issue submission cooldown triggered after repeated rejected reports.",
                payload={
                    "recent_rejection_count": recent_rejection_count,
                    "window_hours": self.config.rejection_cooldown_window_hours,
                },
                commit=True,
            )
            raise TooManyRequestsError(
                (
                    "Recent reports from this account need revision before more "
                    "submissions can be accepted."
                ),
                details={"retry_after_hours": self.config.rejection_cooldown_window_hours},
            )

        from app.schemas.issue import IssueDuplicateSuggestionRequest
        from app.services.duplicate_detection import DuplicateDetectionService

        duplicate_result = await DuplicateDetectionService(self.session).find_duplicate_candidates(
            IssueDuplicateSuggestionRequest(
                title=payload.title,
                short_description=payload.short_description,
                latitude=payload.latitude,
                longitude=payload.longitude,
                category_id=payload.category_id,
            )
        )
        if duplicate_result.status != "no_match":
            recent_duplicate_attempts = int(
                await self.session.scalar(
                    select(func.count(IntegrityEvent.id)).where(
                        IntegrityEvent.user_id == user.id,
                        IntegrityEvent.event_type == EVENT_DUPLICATE_SUBMISSION_ATTEMPT,
                        IntegrityEvent.created_at >= duplicate_cutoff,
                    )
                )
                or 0
            )
            severity = (
                IntegrityEventSeverity.HIGH
                if duplicate_result.status == "high_confidence_duplicate"
                and recent_duplicate_attempts >= self.config.duplicate_attempt_limit
                else IntegrityEventSeverity.MEDIUM
                if duplicate_result.status == "high_confidence_duplicate"
                else IntegrityEventSeverity.LOW
            )
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_DUPLICATE_SUBMISSION_ATTEMPT,
                severity=severity,
                summary=(
                    "Submission closely overlaps with existing nearby issues."
                    if duplicate_result.status == "high_confidence_duplicate"
                    else "Submission overlaps with nearby issues already in the system."
                ),
                payload={
                    "duplicate_status": duplicate_result.status,
                    "match_issue_ids": [
                        str(match.existing_issue_id)
                        for match in duplicate_result.matches
                    ],
                    "top_similarity_score": (
                        duplicate_result.matches[0].similarity_score
                        if duplicate_result.matches
                        else None
                    ),
                },
            )
            if (
                duplicate_result.status == "high_confidence_duplicate"
                and recent_duplicate_attempts >= self.config.duplicate_attempt_limit
            ):
                await self.record_event(
                    user_id=user.id,
                    event_type=EVENT_ISSUE_SUBMISSION_RATE_LIMITED,
                    severity=IntegrityEventSeverity.HIGH,
                    summary=(
                        "Duplicate-submission cooldown triggered after repeated "
                        "high-confidence matches."
                    ),
                    payload={
                        "recent_duplicate_attempts": recent_duplicate_attempts + 1,
                        "window_days": self.config.duplicate_attempt_window_days,
                        "match_issue_id": (
                            str(duplicate_result.matches[0].existing_issue_id)
                            if duplicate_result.matches
                            else None
                        ),
                    },
                    commit=True,
                )
                raise TooManyRequestsError(
                    (
                        "A very similar issue has already been submitted repeatedly "
                        "from this account. Please support the existing issue instead "
                        "of posting another duplicate right now."
                    ),
                    details={
                        "recommended_action": "support_existing_issue",
                        "match_issue_id": str(duplicate_result.matches[0].existing_issue_id)
                        if duplicate_result.matches
                        else None,
                    },
                )

        return duplicate_result

    async def guard_feedback(
        self,
        *,
        user: User,
        issue: Issue,
        action: SwipeDirection,
    ) -> None:
        if action == SwipeDirection.SUPPORT and issue.author_id == user.id:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_SELF_SUPPORT_BLOCKED,
                severity=IntegrityEventSeverity.HIGH,
                entity_type="issue",
                entity_id=issue.id,
                summary="Account attempted to support its own issue.",
                payload={"action": action.value},
                commit=True,
            )
            raise ConflictError("You cannot support your own issue.")

        cutoff = datetime.now(UTC) - timedelta(seconds=self.config.feedback_window_seconds)
        recent_feedback_events = int(
            await self.session.scalar(
                select(func.count(IntegrityEvent.id)).where(
                    IntegrityEvent.user_id == user.id,
                    IntegrityEvent.event_type.in_(
                        (
                            EVENT_FEEDBACK_ACTION,
                            EVENT_SUPPORT_EXISTING_ACTION,
                        )
                    ),
                    IntegrityEvent.created_at >= cutoff,
                )
            )
            or 0
        )
        if recent_feedback_events >= self.config.feedback_limit:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_FEEDBACK_RATE_LIMITED,
                severity=IntegrityEventSeverity.HIGH,
                entity_type="issue",
                entity_id=issue.id,
                summary="Feedback velocity exceeded the allowed burst threshold.",
                payload={
                    "recent_feedback_events": recent_feedback_events,
                    "window_seconds": self.config.feedback_window_seconds,
                },
                commit=True,
            )
            raise TooManyRequestsError(
                "You are reacting too quickly. Please slow down before sending more feedback.",
                details={"retry_after_seconds": self.config.feedback_window_seconds},
            )

        if action == SwipeDirection.SUPPORT:
            same_author_cutoff = datetime.now(UTC) - timedelta(
                minutes=self.config.same_author_support_window_minutes
            )
            same_author_support_count = int(
                await self.session.scalar(
                    select(func.count(SwipeFeedback.id))
                    .join(Issue, SwipeFeedback.issue_id == Issue.id)
                    .where(
                        SwipeFeedback.user_id == user.id,
                        SwipeFeedback.direction == SwipeDirection.SUPPORT,
                        SwipeFeedback.updated_at >= same_author_cutoff,
                        Issue.author_id == issue.author_id,
                    )
                )
                or 0
            )
            if same_author_support_count >= self.config.same_author_support_limit:
                await self.record_event(
                    user_id=user.id,
                    event_type=EVENT_FEEDBACK_PATTERN_WARNING,
                    severity=IntegrityEventSeverity.MEDIUM,
                    entity_type="user",
                    entity_id=issue.author_id,
                    summary="Rapid support concentrated on a single author's issues.",
                    payload={
                        "same_author_support_count": same_author_support_count,
                        "window_minutes": self.config.same_author_support_window_minutes,
                    },
                )

    async def guard_ticket_creation(self, *, user: User) -> None:
        cutoff = datetime.now(UTC) - timedelta(minutes=self.config.ticket_window_minutes)
        recent_ticket_count = int(
            await self.session.scalar(
                select(func.count(SupportTicket.id)).where(
                    SupportTicket.author_id == user.id,
                    SupportTicket.created_at >= cutoff,
                )
            )
            or 0
        )
        if recent_ticket_count >= self.config.ticket_limit:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_TICKET_RATE_LIMITED,
                severity=IntegrityEventSeverity.MEDIUM,
                summary="Support ticket rate limit triggered.",
                payload={
                    "recent_ticket_count": recent_ticket_count,
                    "window_minutes": self.config.ticket_window_minutes,
                },
                commit=True,
            )
            raise TooManyRequestsError(
                (
                    "Too many support tickets were opened in a short period. "
                    "Please wait before creating another one."
                ),
                details={"retry_after_minutes": self.config.ticket_window_minutes},
            )

    async def guard_rewrite_request(self, *, user: User | None) -> None:
        if user is None:
            return

        cutoff = datetime.now(UTC) - timedelta(minutes=self.config.rewrite_window_minutes)
        recent_rewrite_count = int(
            await self.session.scalar(
                select(func.count(IntegrityEvent.id)).where(
                    IntegrityEvent.user_id == user.id,
                    IntegrityEvent.event_type == EVENT_REWRITE_REQUEST,
                    IntegrityEvent.created_at >= cutoff,
                )
            )
            or 0
        )
        if recent_rewrite_count >= self.config.rewrite_limit:
            await self.record_event(
                user_id=user.id,
                event_type=EVENT_REWRITE_RATE_LIMITED,
                severity=IntegrityEventSeverity.MEDIUM,
                summary="Constructive rewrite endpoint hit its short-term rate limit.",
                payload={
                    "recent_rewrite_count": recent_rewrite_count,
                    "window_minutes": self.config.rewrite_window_minutes,
                },
                commit=True,
            )
            raise TooManyRequestsError(
                (
                    "The rewrite assist is being used too quickly from this account. "
                    "Please pause briefly and try again."
                ),
                details={"retry_after_minutes": self.config.rewrite_window_minutes},
            )

    async def record_issue_submission_created(
        self,
        *,
        user: User,
        issue: Issue,
        duplicate_status: str | None = None,
    ) -> None:
        await self.record_event(
            user_id=user.id,
            event_type=EVENT_ISSUE_SUBMISSION_CREATED,
            severity=IntegrityEventSeverity.LOW,
            entity_type="issue",
            entity_id=issue.id,
            summary="Issue submission accepted into the moderation pipeline.",
            payload={
                "issue_status": issue.status.value,
                "duplicate_status": duplicate_status,
            },
        )

    async def record_feedback_action(
        self,
        *,
        user: User,
        issue: Issue,
        action: SwipeDirection,
        support_changed: bool,
    ) -> None:
        await self.record_event(
            user_id=user.id,
            event_type=EVENT_FEEDBACK_ACTION,
            severity=IntegrityEventSeverity.LOW,
            entity_type="issue",
            entity_id=issue.id,
            summary="Public issue feedback recorded.",
            payload={
                "action": action.value,
                "support_changed": support_changed,
                "issue_author_id": str(issue.author_id),
            },
        )

    async def record_support_existing_action(
        self,
        *,
        user: User,
        issue: Issue,
        support_changed: bool,
        duplicate_status: str = "supported_existing",
    ) -> None:
        await self.record_event(
            user_id=user.id,
            event_type=EVENT_SUPPORT_EXISTING_ACTION,
            severity=IntegrityEventSeverity.LOW,
            entity_type="issue",
            entity_id=issue.id,
            summary="Existing issue was supported instead of creating a new duplicate.",
            payload={
                "support_changed": support_changed,
                "duplicate_status": duplicate_status,
                "issue_author_id": str(issue.author_id),
            },
        )

    async def record_ticket_created(
        self,
        *,
        user: User,
        ticket: SupportTicket,
    ) -> None:
        await self.record_event(
            user_id=user.id,
            event_type=EVENT_TICKET_CREATED,
            severity=IntegrityEventSeverity.LOW,
            entity_type="support_ticket",
            entity_id=ticket.id,
            summary="Support ticket created.",
            payload={
                "ticket_type": ticket.ticket_type.value,
                "issue_id": str(ticket.issue_id) if ticket.issue_id else None,
            },
        )

    async def record_rewrite_request(self, *, user: User | None) -> None:
        if user is None:
            return

        await self.record_event(
            user_id=user.id,
            event_type=EVENT_REWRITE_REQUEST,
            severity=IntegrityEventSeverity.LOW,
            summary="Constructive rewrite assist used.",
            payload={},
        )

    async def record_moderation_outcome(
        self,
        *,
        issue: Issue,
        status: ModerationResultStatus,
        machine_reason_codes: list[str],
    ) -> None:
        event_type = EVENT_MODERATION_APPROVED
        severity = IntegrityEventSeverity.LOW
        summary = "Issue cleared moderation."

        if status == ModerationResultStatus.REJECTED:
            event_type = EVENT_MODERATION_REJECTED
            severity = IntegrityEventSeverity.MEDIUM
            summary = "Issue was rejected by moderation."
        elif status == ModerationResultStatus.NEEDS_REVIEW:
            event_type = EVENT_MODERATION_REVIEW
            severity = IntegrityEventSeverity.MEDIUM
            summary = "Issue needs manual moderation review."

        await self.record_event(
            user_id=issue.author_id,
            event_type=event_type,
            severity=severity,
            entity_type="issue",
            entity_id=issue.id,
            summary=summary,
            payload={
                "issue_status": issue.status.value,
                "moderation_status": status.value,
                "machine_reason_codes": machine_reason_codes,
            },
        )

    async def record_event(
        self,
        *,
        user_id: UUID,
        event_type: str,
        severity: IntegrityEventSeverity,
        summary: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip_hash: str | None = None,
        device_fingerprint_hash: str | None = None,
        commit: bool = False,
    ) -> IntegrityEvent:
        event = IntegrityEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            payload=payload or {},
            ip_hash=ip_hash,
            device_fingerprint_hash=device_fingerprint_hash,
        )
        self.session.add(event)
        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        else:
            await self.session.flush()
        return event

    async def _count_recent_event_types(
        self,
        user_id: UUID,
        *,
        since: datetime,
    ) -> dict[str, int]:
        rows = await self.session.execute(
            select(IntegrityEvent.event_type, func.count(IntegrityEvent.id))
            .where(
                IntegrityEvent.user_id == user_id,
                IntegrityEvent.created_at >= since,
            )
            .group_by(IntegrityEvent.event_type)
        )
        return {event_type: int(count) for event_type, count in rows.all()}

    async def _count_recent_event_severities(
        self,
        user_id: UUID,
        *,
        since: datetime,
    ) -> dict[IntegrityEventSeverity, int]:
        rows = await self.session.execute(
            select(IntegrityEvent.severity, func.count(IntegrityEvent.id))
            .where(
                IntegrityEvent.user_id == user_id,
                IntegrityEvent.created_at >= since,
            )
            .group_by(IntegrityEvent.severity)
        )
        return {severity: int(count) for severity, count in rows.all()}

    async def _count_admin_sanctions(self, user_id: UUID) -> int:
        logs = (
            await self.session.scalars(
                select(AdminActionLog).where(
                    AdminActionLog.entity_type == "user",
                    AdminActionLog.entity_id == user_id,
                )
            )
        ).all()
        return sum(
            1
            for log in logs
            if any(keyword in log.action.lower() for keyword in SANCTION_ACTION_KEYWORDS)
        )

    @staticmethod
    def _build_factor(
        *,
        name: str,
        label: str,
        signal: float,
        points: float,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "name": name,
            "label": label,
            "effect": "risk",
            "signal": round(signal, 3),
            "points": round(points, 3),
            "details": details,
        }

    @staticmethod
    def _summary_for_level(
        level: AbuseRiskLevel,
        reasons: list[dict[str, Any]],
    ) -> str:
        if level == AbuseRiskLevel.HIGH:
            return (
                "High abuse risk. Recent behavior suggests manipulation or "
                "repeated low-quality activity."
            )
        if level == AbuseRiskLevel.MEDIUM:
            return (
                "Medium abuse risk. The account shows patterns that should be "
                "monitored or softly constrained."
            )
        if reasons:
            return "Low abuse risk with a small number of watchlist signals."
        return "Low abuse risk. No meaningful manipulation pattern is currently visible."

    @staticmethod
    def _recommended_actions(level: AbuseRiskLevel) -> tuple[str, ...]:
        if level == AbuseRiskLevel.HIGH:
            return (
                "Apply temporary cooldowns to high-frequency actions.",
                "Route future submissions to closer moderation review.",
                "Inspect recent integrity events and admin sanctions.",
            )
        if level == AbuseRiskLevel.MEDIUM:
            return (
                "Monitor activity for burst escalation.",
                "Keep reaction and submission rate limits active.",
            )
        return ("Monitor routinely.",)
