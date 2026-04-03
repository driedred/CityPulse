from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import (
    AdminActionLog,
    IntegrityEvent,
    Issue,
    SupportTicket,
    SwipeFeedback,
    User,
    UserIntegritySnapshot,
)
from app.models.enums import (
    AbuseRiskLevel,
    IssueStatus,
    SupportTicketStatus,
    SwipeDirection,
)
from app.schemas.user import (
    AdminUserIdentityRead,
    IntegrityEventRead,
    IntegrityFactorRead,
    UserIntegrityCompactRead,
    UserIntegrityDetailRead,
    UserIntegritySummaryRead,
)
from app.services.anti_abuse import (
    EVENT_DUPLICATE_SUBMISSION_ATTEMPT,
    EVENT_FEEDBACK_PATTERN_WARNING,
    EVENT_FEEDBACK_RATE_LIMITED,
    EVENT_MODERATION_REJECTED,
    EVENT_MODERATION_REVIEW,
    SANCTION_ACTION_KEYWORDS,
    AntiAbuseService,
)
from app.services.intelligence_utils import clamp, ensure_utc, saturating_ratio


@dataclass(frozen=True)
class TrustScoreWeights:
    approved_submissions: float = 14.0
    durable_usefulness: float = 10.0
    meaningful_support: float = 8.0
    confirmed_resolution_proxy: float = 8.0
    account_age: float = 6.0
    consistent_behavior: float = 5.0
    moderation_rejections: float = 14.0
    duplicate_spam: float = 10.0
    low_signal_feedback: float = 7.0
    suspicious_behavior: float = 8.0
    admin_sanctions: float = 14.0


@dataclass(frozen=True)
class TrustScoreConfig:
    score_version: str = "trust-v1"
    max_snapshot_age_minutes: int = 120
    durable_issue_age_days: int = 7
    suspicious_activity_window_days: int = 30
    baseline_score: float = 55.0
    minimum_score: float = 25.0
    maximum_score: float = 95.0
    minimum_weight_multiplier: float = 0.88
    maximum_weight_multiplier: float = 1.16
    approved_issue_saturation: float = 8.0
    durable_issue_saturation: float = 6.0
    support_action_saturation: float = 24.0
    resolved_ticket_saturation: float = 4.0
    rejection_saturation: float = 4.0
    duplicate_spam_saturation: float = 4.0
    low_signal_feedback_saturation: float = 10.0
    suspicious_event_saturation: float = 6.0
    sanctions_saturation: float = 3.0
    weights: TrustScoreWeights = field(default_factory=TrustScoreWeights)


class TrustScoreService:
    """Maintain bounded internal trust scores for ranking and abuse resistance.

    The score is intentionally conservative: new users start near a neutral
    baseline, good history raises support weighting gradually, and abuse or
    consistently rejected activity reduces weighting without driving it to zero.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        config: TrustScoreConfig | None = None,
    ) -> None:
        self.session = session
        self.config = config or TrustScoreConfig()
        self.anti_abuse = AntiAbuseService(session)

    async def ensure_user_snapshots(
        self,
        user_ids: Sequence[UUID],
        *,
        commit: bool = True,
    ) -> dict[UUID, UserIntegritySnapshot]:
        unique_user_ids = list(dict.fromkeys(user_ids))
        if not unique_user_ids:
            return {}

        snapshots_result = await self.session.scalars(
            select(UserIntegritySnapshot).where(UserIntegritySnapshot.user_id.in_(unique_user_ids))
        )
        snapshots = {snapshot.user_id: snapshot for snapshot in snapshots_result.all()}
        now = datetime.now(UTC)
        stale_user_ids = [
            user_id
            for user_id in unique_user_ids
            if self._snapshot_is_stale(snapshots.get(user_id), now=now)
        ]

        for user_id in stale_user_ids:
            snapshots[user_id] = await self.recalculate_user(user_id, commit=False)

        if stale_user_ids:
            if commit:
                await self.session.commit()
            else:
                await self.session.flush()

        return snapshots

    async def recalculate_user(
        self,
        user_id: UUID,
        *,
        commit: bool = False,
    ) -> UserIntegritySnapshot:
        user = await self.session.scalar(select(User).where(User.id == user_id))
        if user is None:
            raise NotFoundError("User was not found.")

        snapshot = await self._build_snapshot(user)
        self.session.add(snapshot)

        if commit:
            await self.session.commit()
            await self.session.refresh(snapshot)
        else:
            await self.session.flush()

        return snapshot

    async def get_weight_multipliers(
        self,
        user_ids: Sequence[UUID],
        *,
        commit: bool = False,
    ) -> dict[UUID, float]:
        snapshots = await self.ensure_user_snapshots(user_ids, commit=commit)
        return {
            user_id: snapshot.trust_weight_multiplier
            for user_id, snapshot in snapshots.items()
        }

    async def _build_snapshot(self, user: User) -> UserIntegritySnapshot:
        authored_status_rows = await self.session.execute(
            select(Issue.status, func.count(Issue.id))
            .where(Issue.author_id == user.id)
            .group_by(Issue.status)
        )
        authored_status_counts = {
            status: int(count) for status, count in authored_status_rows.all()
        }
        authored_issue_count = sum(authored_status_counts.values())
        approved_issue_count = (
            authored_status_counts.get(IssueStatus.APPROVED, 0)
            + authored_status_counts.get(IssueStatus.PUBLISHED, 0)
        )
        rejected_issue_count = authored_status_counts.get(IssueStatus.REJECTED, 0)

        durable_cutoff = datetime.now(UTC) - timedelta(days=self.config.durable_issue_age_days)
        durable_issue_count = int(
            await self.session.scalar(
                select(func.count(Issue.id)).where(
                    Issue.author_id == user.id,
                    Issue.status.in_((IssueStatus.APPROVED, IssueStatus.PUBLISHED)),
                    Issue.created_at <= durable_cutoff,
                )
            )
            or 0
        )
        meaningful_support_count = int(
            await self.session.scalar(
                select(func.count(func.distinct(SwipeFeedback.issue_id)))
                .join(Issue, SwipeFeedback.issue_id == Issue.id)
                .where(
                    SwipeFeedback.user_id == user.id,
                    SwipeFeedback.direction == SwipeDirection.SUPPORT,
                    Issue.author_id != user.id,
                )
            )
            or 0
        )
        resolved_ticket_count = int(
            await self.session.scalar(
                select(func.count(func.distinct(SupportTicket.id)))
                .join(Issue, SupportTicket.issue_id == Issue.id)
                .where(
                    Issue.author_id == user.id,
                    SupportTicket.status.in_(
                        (
                            SupportTicketStatus.RESOLVED,
                            SupportTicketStatus.CLOSED,
                        )
                    ),
                )
            )
            or 0
        )
        support_received_count = int(
            await self.session.scalar(
                select(func.count(SwipeFeedback.id))
                .join(Issue, SwipeFeedback.issue_id == Issue.id)
                .where(
                    Issue.author_id == user.id,
                    SwipeFeedback.direction == SwipeDirection.SUPPORT,
                )
            )
            or 0
        )
        less_like_this_count = int(
            await self.session.scalar(
                select(func.count(SwipeFeedback.id))
                .join(Issue, SwipeFeedback.issue_id == Issue.id)
                .where(
                    Issue.author_id == user.id,
                    SwipeFeedback.direction == SwipeDirection.LESS_LIKE_THIS,
                )
            )
            or 0
        )

        suspicious_cutoff = datetime.now(UTC) - timedelta(
            days=self.config.suspicious_activity_window_days
        )
        suspicious_event_count = int(
            await self.session.scalar(
                select(func.count(IntegrityEvent.id)).where(
                    IntegrityEvent.user_id == user.id,
                    IntegrityEvent.created_at >= suspicious_cutoff,
                    IntegrityEvent.event_type.in_(
                        (
                            EVENT_FEEDBACK_RATE_LIMITED,
                            EVENT_FEEDBACK_PATTERN_WARNING,
                            EVENT_DUPLICATE_SUBMISSION_ATTEMPT,
                            EVENT_MODERATION_REJECTED,
                            EVENT_MODERATION_REVIEW,
                        )
                    ),
                )
            )
            or 0
        )
        duplicate_spam_count = int(
            await self.session.scalar(
                select(func.count(IntegrityEvent.id)).where(
                    IntegrityEvent.user_id == user.id,
                    IntegrityEvent.event_type == EVENT_DUPLICATE_SUBMISSION_ATTEMPT,
                )
            )
            or 0
        )
        sanction_count = await self._count_admin_sanctions(user.id)
        abuse_assessment = await self.anti_abuse.assess_user(user.id)

        account_age_days = self._days_since(user.created_at)
        approved_signal = clamp(
            saturating_ratio(approved_issue_count, self.config.approved_issue_saturation) * 0.5
            + clamp(approved_issue_count / max(authored_issue_count, 1)) * 0.5
        )
        durable_signal = saturating_ratio(
            durable_issue_count,
            self.config.durable_issue_saturation,
        )
        support_signal = saturating_ratio(
            meaningful_support_count,
            self.config.support_action_saturation,
        )
        resolution_signal = saturating_ratio(
            resolved_ticket_count,
            self.config.resolved_ticket_saturation,
        )
        account_age_signal = clamp(account_age_days / 365)
        consistency_signal = clamp(
            account_age_signal * 0.4
            + (
                1
                - saturating_ratio(
                    suspicious_event_count,
                    self.config.suspicious_event_saturation,
                )
            )
            * 0.6
        )
        rejection_signal = clamp(
            saturating_ratio(rejected_issue_count, self.config.rejection_saturation) * 0.65
            + (rejected_issue_count / max(authored_issue_count, 1)) * 0.35
        )
        duplicate_spam_signal = saturating_ratio(
            duplicate_spam_count,
            self.config.duplicate_spam_saturation,
        )
        low_signal_feedback_signal = clamp(
            less_like_this_count / max(support_received_count + less_like_this_count, 1)
            * 0.55
            + saturating_ratio(
                less_like_this_count,
                self.config.low_signal_feedback_saturation,
            )
            * 0.45
        )
        suspicious_behavior_signal = saturating_ratio(
            suspicious_event_count,
            self.config.suspicious_event_saturation,
        )
        sanction_signal = saturating_ratio(
            sanction_count,
            self.config.sanctions_saturation,
        )

        weights = self.config.weights
        positive_points = (
            approved_signal * weights.approved_submissions
            + durable_signal * weights.durable_usefulness
            + support_signal * weights.meaningful_support
            + resolution_signal * weights.confirmed_resolution_proxy
            + account_age_signal * weights.account_age
            + consistency_signal * weights.consistent_behavior
        )
        negative_points = (
            rejection_signal * weights.moderation_rejections
            + duplicate_spam_signal * weights.duplicate_spam
            + low_signal_feedback_signal * weights.low_signal_feedback
            + suspicious_behavior_signal * weights.suspicious_behavior
            + sanction_signal * weights.admin_sanctions
        )
        trust_score = round(
            clamp(
                self.config.baseline_score + positive_points - negative_points,
                minimum=self.config.minimum_score,
                maximum=self.config.maximum_score,
            ),
            1,
        )
        normalized_score = clamp(
            (trust_score - self.config.minimum_score)
            / max(self.config.maximum_score - self.config.minimum_score, 1),
        )
        trust_weight_multiplier = round(
            self.config.minimum_weight_multiplier
            + normalized_score
            * (
                self.config.maximum_weight_multiplier
                - self.config.minimum_weight_multiplier
            ),
            3,
        )

        trust_factors = [
            self._factor(
                name="approved_submissions",
                label="Repeated submissions that pass moderation",
                effect="positive",
                signal=approved_signal,
                points=approved_signal * weights.approved_submissions,
                details={
                    "approved_issue_count": approved_issue_count,
                    "authored_issue_count": authored_issue_count,
                },
            ),
            self._factor(
                name="durable_usefulness",
                label="Submissions that remain useful over time",
                effect="positive",
                signal=durable_signal,
                points=durable_signal * weights.durable_usefulness,
                details={
                    "durable_issue_count": durable_issue_count,
                    "durable_age_days": self.config.durable_issue_age_days,
                },
            ),
            self._factor(
                name="meaningful_support",
                label="Meaningful support activity",
                effect="positive",
                signal=support_signal,
                points=support_signal * weights.meaningful_support,
                details={"meaningful_support_count": meaningful_support_count},
            ),
            self._factor(
                name="confirmed_resolution_proxy",
                label="Resolved or confirmed issue proxy",
                effect="positive",
                signal=resolution_signal,
                points=resolution_signal * weights.confirmed_resolution_proxy,
                details={"resolved_ticket_count": resolved_ticket_count},
            ),
            self._factor(
                name="account_age",
                label="Consistent account age",
                effect="positive",
                signal=account_age_signal,
                points=account_age_signal * weights.account_age,
                details={"account_age_days": round(account_age_days, 1)},
            ),
            self._factor(
                name="consistent_behavior",
                label="Stable account behavior over time",
                effect="positive",
                signal=consistency_signal,
                points=consistency_signal * weights.consistent_behavior,
                details={"suspicious_event_count": suspicious_event_count},
            ),
            self._factor(
                name="moderation_rejections",
                label="Repeated rejected submissions",
                effect="negative",
                signal=rejection_signal,
                points=-rejection_signal * weights.moderation_rejections,
                details={"rejected_issue_count": rejected_issue_count},
            ),
            self._factor(
                name="duplicate_spam",
                label="Repeated duplicate-posting behavior",
                effect="negative",
                signal=duplicate_spam_signal,
                points=-duplicate_spam_signal * weights.duplicate_spam,
                details={"duplicate_spam_count": duplicate_spam_count},
            ),
            self._factor(
                name="low_signal_feedback",
                label="Low-signal engagement patterns",
                effect="negative",
                signal=low_signal_feedback_signal,
                points=-low_signal_feedback_signal * weights.low_signal_feedback,
                details={
                    "less_like_this_count": less_like_this_count,
                    "support_received_count": support_received_count,
                },
            ),
            self._factor(
                name="suspicious_behavior",
                label="Suspicious bursts or scripted-like activity",
                effect="negative",
                signal=suspicious_behavior_signal,
                points=-suspicious_behavior_signal * weights.suspicious_behavior,
                details={"suspicious_event_count": suspicious_event_count},
            ),
            self._factor(
                name="admin_sanctions",
                label="Admin sanctions or restrictions",
                effect="negative",
                signal=sanction_signal,
                points=-sanction_signal * weights.admin_sanctions,
                details={"sanction_count": sanction_count},
            ),
        ]

        trust_breakdown = {
            "summary": self._trust_summary(trust_score, abuse_assessment.risk_level),
            "factors": trust_factors,
            "calculation_notes": [
                "New users start near a neutral baseline instead of being heavily discounted.",
                "Weight multipliers are bounded so trust influences ranking without dominating it.",
                "Negative signals matter most when they repeat over time or occur in bursts.",
            ],
        }
        abuse_summary = {
            "summary": abuse_assessment.summary,
            "factors": list(abuse_assessment.reasons),
            "recommended_actions": list(abuse_assessment.recommended_actions),
            "metrics": abuse_assessment.metrics,
        }
        metrics = {
            "trust_score_version": self.config.score_version,
            "abuse_risk_level": abuse_assessment.risk_level.value,
            "abuse_risk_score": abuse_assessment.risk_score,
            "authored_issue_count": authored_issue_count,
            "approved_issue_count": approved_issue_count,
            "durable_issue_count": durable_issue_count,
            "rejected_issue_count": rejected_issue_count,
            "meaningful_support_count": meaningful_support_count,
            "resolved_ticket_count": resolved_ticket_count,
            "support_received_count": support_received_count,
            "less_like_this_count": less_like_this_count,
            "suspicious_event_count": suspicious_event_count,
            "duplicate_spam_count": duplicate_spam_count,
            "sanction_count": sanction_count,
        }

        existing_snapshot = await self.session.scalar(
            select(UserIntegritySnapshot).where(UserIntegritySnapshot.user_id == user.id)
        )
        if existing_snapshot is None:
            return UserIntegritySnapshot(
                user_id=user.id,
                trust_score=trust_score,
                trust_weight_multiplier=trust_weight_multiplier,
                abuse_risk_level=abuse_assessment.risk_level,
                abuse_risk_score=abuse_assessment.risk_score,
                sanction_count=sanction_count,
                trust_breakdown=trust_breakdown,
                abuse_summary=abuse_summary,
                metrics=metrics,
            )

        existing_snapshot.trust_score = trust_score
        existing_snapshot.trust_weight_multiplier = trust_weight_multiplier
        existing_snapshot.abuse_risk_level = abuse_assessment.risk_level
        existing_snapshot.abuse_risk_score = abuse_assessment.risk_score
        existing_snapshot.sanction_count = sanction_count
        existing_snapshot.trust_breakdown = trust_breakdown
        existing_snapshot.abuse_summary = abuse_summary
        existing_snapshot.metrics = metrics
        return existing_snapshot

    def _snapshot_is_stale(
        self,
        snapshot: UserIntegritySnapshot | None,
        *,
        now: datetime | None = None,
    ) -> bool:
        if snapshot is None:
            return True
        version = snapshot.metrics.get("trust_score_version")
        if version != self.config.score_version:
            return True

        reference_time = now or datetime.now(UTC)
        return ensure_utc(snapshot.updated_at) < reference_time - timedelta(
            minutes=self.config.max_snapshot_age_minutes
        )

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
    def _days_since(value: datetime) -> float:
        return max((datetime.now(UTC) - ensure_utc(value)).total_seconds() / 86_400, 0.0)

    @staticmethod
    def _factor(
        *,
        name: str,
        label: str,
        effect: str,
        signal: float,
        points: float,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "name": name,
            "label": label,
            "effect": effect,
            "signal": round(signal, 3),
            "points": round(points, 3),
            "details": details,
        }

    @staticmethod
    def _trust_summary(score: float, abuse_risk_level: AbuseRiskLevel) -> str:
        if score >= 75 and abuse_risk_level == AbuseRiskLevel.LOW:
            return "Established constructive contributor."
        if score >= 60:
            return "Generally reliable civic participant."
        if score >= 45:
            return "Neutral baseline trust. The account is still building history."
        return "Reduced trust weighting due to repeated quality or integrity concerns."


def serialize_admin_identity(user: User) -> AdminUserIdentityRead:
    return AdminUserIdentityRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        preferred_locale=user.preferred_locale,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def serialize_integrity_compact(
    user: User,
    snapshot: UserIntegritySnapshot | None = None,
) -> UserIntegrityCompactRead | None:
    snapshot_value = snapshot or user.integrity_snapshot
    if snapshot_value is None:
        return None

    return UserIntegrityCompactRead(
        user=serialize_admin_identity(user),
        trust_score=snapshot_value.trust_score,
        trust_weight_multiplier=snapshot_value.trust_weight_multiplier,
        abuse_risk_level=snapshot_value.abuse_risk_level,
        abuse_risk_score=snapshot_value.abuse_risk_score,
        sanction_count=snapshot_value.sanction_count,
        summary=_compact_summary(snapshot_value),
        updated_at=snapshot_value.updated_at,
    )


def serialize_integrity_summary(
    user: User,
    snapshot: UserIntegritySnapshot | None = None,
) -> UserIntegritySummaryRead | None:
    snapshot_value = snapshot or user.integrity_snapshot
    if snapshot_value is None:
        return None

    compact = serialize_integrity_compact(user, snapshot_value)
    if compact is None:
        return None

    return UserIntegritySummaryRead(
        **compact.model_dump(),
        trust_factors=[
            IntegrityFactorRead.model_validate(factor)
            for factor in snapshot_value.trust_breakdown.get("factors", [])
        ],
        abuse_factors=[
            IntegrityFactorRead.model_validate(factor)
            for factor in snapshot_value.abuse_summary.get("factors", [])
        ],
        recommended_actions=list(
            snapshot_value.abuse_summary.get("recommended_actions", [])
        ),
        metrics=snapshot_value.metrics,
    )


def serialize_integrity_event(event: IntegrityEvent) -> IntegrityEventRead:
    return IntegrityEventRead(
        id=event.id,
        event_type=event.event_type,
        severity=event.severity,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        summary=event.summary,
        payload=event.payload,
        created_at=event.created_at,
    )


def serialize_integrity_detail(
    user: User,
    *,
    events: Sequence[IntegrityEvent],
    snapshot: UserIntegritySnapshot | None = None,
) -> UserIntegrityDetailRead | None:
    summary = serialize_integrity_summary(user, snapshot)
    if summary is None:
        return None

    return UserIntegrityDetailRead(
        **summary.model_dump(),
        recent_events=[serialize_integrity_event(event) for event in events],
    )


def _compact_summary(snapshot: UserIntegritySnapshot) -> str | None:
    if snapshot.abuse_risk_level != AbuseRiskLevel.LOW:
        return snapshot.abuse_summary.get("summary")
    return snapshot.trust_breakdown.get("summary")
