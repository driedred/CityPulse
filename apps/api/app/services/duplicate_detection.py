from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Issue
from app.models.enums import IssueStatus
from app.schemas.issue import (
    IssueCategoryRead,
    IssueDuplicateSuggestionRead,
    IssueDuplicateSuggestionRequest,
    IssueDuplicateSuggestionResponse,
    PublicIssueSummaryRead,
)
from app.services.impact_scores import ImpactScoreService
from app.services.intelligence_utils import (
    blended_text_similarity,
    clamp,
    distance_km,
    ensure_utc,
)


@dataclass(frozen=True)
class DuplicateDetectionConfig:
    possible_distance_km: float = 1.6
    high_confidence_distance_km: float = 0.35
    possible_similarity_threshold: float = 0.38
    high_confidence_similarity_threshold: float = 0.74
    recent_window_days: int = 180
    max_candidates: int = 80


class DuplicateDetectionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        config: DuplicateDetectionConfig | None = None,
    ) -> None:
        self.session = session
        self.config = config or DuplicateDetectionConfig()

    async def find_duplicate_candidates(
        self,
        payload: IssueDuplicateSuggestionRequest,
    ) -> IssueDuplicateSuggestionResponse:
        cutoff = datetime.now(UTC) - timedelta(days=self.config.recent_window_days)
        impact_scores = ImpactScoreService(self.session)
        candidate_issues = (
            await self.session.scalars(
                select(Issue)
                .where(
                    Issue.status.in_(
                        (
                            IssueStatus.PENDING_MODERATION,
                            IssueStatus.APPROVED,
                            IssueStatus.PUBLISHED,
                        )
                    ),
                    Issue.created_at >= cutoff,
                )
                .options(
                    selectinload(Issue.category),
                    selectinload(Issue.attachments),
                    selectinload(Issue.impact_snapshot),
                )
                .order_by(Issue.created_at.desc())
                .limit(self.config.max_candidates)
            )
        ).all()

        impact_snapshots = await impact_scores.ensure_issue_metrics(
            candidate_issues,
            commit=True,
        )
        matches: list[IssueDuplicateSuggestionRead] = []

        for issue in candidate_issues:
            distance = distance_km(
                payload.latitude,
                payload.longitude,
                issue.latitude,
                issue.longitude,
            )
            if distance > self.config.possible_distance_km:
                continue

            text_similarity = blended_text_similarity(
                title_left=payload.title,
                title_right=issue.title,
                description_left=payload.short_description,
                description_right=issue.short_description,
            )
            category_match = (
                payload.category_id is not None and issue.category_id == payload.category_id
            )
            issue_age_days = max((datetime.now(UTC) - ensure_utc(issue.created_at)).days, 0)
            time_relevance = clamp(
                1 - issue_age_days / max(self.config.recent_window_days, 1)
            )
            geo_signal = clamp(1 - distance / self.config.possible_distance_km)
            category_signal = 1.0 if category_match else 0.0
            similarity_score = round(
                clamp(
                    text_similarity * 0.55
                    + geo_signal * 0.25
                    + category_signal * 0.1
                    + time_relevance * 0.1
                ),
                3,
            )
            if similarity_score < self.config.possible_similarity_threshold:
                continue

            high_confidence = (
                similarity_score >= self.config.high_confidence_similarity_threshold
                and distance <= self.config.high_confidence_distance_km
                and text_similarity >= 0.6
            )
            recommended_action = (
                "support_existing"
                if high_confidence or similarity_score >= 0.55
                else "review_before_submit"
            )
            reason_breakdown = self._reason_breakdown(
                distance=distance,
                text_similarity=text_similarity,
                category_match=category_match,
            )

            matches.append(
                IssueDuplicateSuggestionRead(
                    issue=self._to_public_summary(issue, impact_snapshots, impact_scores),
                    existing_issue_id=issue.id,
                    similarity_score=similarity_score,
                    reason_breakdown=reason_breakdown,
                    distance_km=round(distance, 2),
                    text_similarity=round(text_similarity, 3),
                    category_match=category_match,
                    recommended_action=recommended_action,
                    image_similarity=None,
                )
            )

        matches.sort(key=lambda match: match.similarity_score, reverse=True)
        status = "no_match"
        if matches:
            top_match = matches[0]
            status = (
                "high_confidence_duplicate"
                if top_match.similarity_score >= self.config.high_confidence_similarity_threshold
                and top_match.distance_km <= self.config.high_confidence_distance_km
                else "possible_duplicates"
            )

        return IssueDuplicateSuggestionResponse(status=status, matches=matches[:4])

    def _reason_breakdown(
        self,
        *,
        distance: float,
        text_similarity: float,
        category_match: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if category_match:
            reasons.append("Same category")
        if distance <= self.config.high_confidence_distance_km:
            reasons.append("Nearly identical location")
        elif distance <= self.config.possible_distance_km:
            reasons.append("Nearby report cluster")
        if text_similarity >= 0.7:
            reasons.append("Strong title and description overlap")
        elif text_similarity >= 0.5:
            reasons.append("Meaningfully similar wording")

        return reasons or ["Potential duplicate"]

    def _to_public_summary(
        self,
        issue: Issue,
        impact_snapshots,
        impact_scores: ImpactScoreService,
    ) -> PublicIssueSummaryRead:
        snapshot = impact_snapshots.get(issue.id)
        support_count = int(snapshot.signals.get("unique_supporters", 0)) if snapshot else 0
        public_score = snapshot.public_impact_score if snapshot else None
        affected_people = snapshot.affected_people_estimate if snapshot else None
        importance_label = (
            impact_scores.importance_label(public_score)
            if public_score is not None
            else None
        )

        return PublicIssueSummaryRead(
            id=issue.id,
            title=issue.title,
            short_description=issue.short_description,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=IssueCategoryRead.model_validate(issue.category),
            location_snippet=f"{issue.latitude:.3f}, {issue.longitude:.3f}",
            support_count=support_count,
            public_impact_score=public_score,
            affected_people_estimate=affected_people,
            importance_label=importance_label,
            cover_image_url=None,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )
