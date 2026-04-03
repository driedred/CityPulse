from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models import Issue, IssueDuplicateLink, IssueImpactSnapshot, SwipeFeedback
from app.models.enums import DuplicateResolutionStatus, IssueStatus, SwipeDirection
from app.schemas.issue import IssueImpactAdminRead, IssueImpactFactorRead, IssuePublicImpactRead
from app.services.intelligence_utils import (
    clamp,
    distance_km,
    ensure_utc,
    normalize_text,
    round_public_people_estimate,
    saturating_ratio,
)
from app.services.trust_scores import TrustScoreService

SCORABLE_STATUSES = (
    IssueStatus.PENDING_MODERATION,
    IssueStatus.APPROVED,
    IssueStatus.PUBLISHED,
)


@dataclass(frozen=True)
class ImpactScoreWeights:
    unique_supporters: float = 0.22
    trust_weighted_support: float = 0.12
    recency: float = 0.14
    category_severity: float = 0.16
    local_density: float = 0.12
    duplicate_aggregation: float = 0.10
    moderation_quality: float = 0.10
    author_trust: float = 0.04


@dataclass(frozen=True)
class ImpactScoreConfig:
    score_version: str = "impact-v1"
    max_snapshot_age_minutes: int = 30
    support_saturation: float = 24.0
    weighted_support_saturation: float = 28.0
    local_density_radius_km: float = 1.2
    local_density_saturation: float = 5.0
    duplicate_cluster_saturation: float = 4.0
    recency_half_life_days: float = 14.0
    related_report_window_days: int = 120
    affected_people_support_multiplier: float = 11.0
    affected_people_density_multiplier: float = 18.0
    affected_people_duplicate_multiplier: float = 22.0
    weights: ImpactScoreWeights = field(default_factory=ImpactScoreWeights)
    location_type_multipliers: dict[str, tuple[str, float]] = field(
        default_factory=lambda: {
            "roads": ("corridor", 1.15),
            "transport": ("transit_stop", 1.25),
            "safety": ("shared_public_space", 1.2),
            "lighting": ("residential_block", 0.95),
        }
    )


@dataclass(frozen=True)
class UserTrustSignal:
    trust_score: float = 55.0
    weight_multiplier: float = 1.0


class ImpactScoreService:
    """Compute and cache civic priority metrics.

    The formula intentionally mixes community demand, geography, quality, and
    bounded trust signals. The stored snapshot is the single source for both the
    public impact number and the admin-only breakdown.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        config: ImpactScoreConfig | None = None,
    ) -> None:
        self.session = session
        self.config = config or ImpactScoreConfig()

    async def ensure_issue_metrics(
        self,
        issues: Sequence[Issue],
        *,
        commit: bool = True,
    ) -> dict[UUID, IssueImpactSnapshot]:
        issue_ids = [issue.id for issue in issues]
        if not issue_ids:
            return {}

        snapshots_result = await self.session.scalars(
            select(IssueImpactSnapshot).where(IssueImpactSnapshot.issue_id.in_(issue_ids))
        )
        snapshots = {snapshot.issue_id: snapshot for snapshot in snapshots_result.all()}
        reference_time = datetime.now(UTC)
        stale_issue_ids = [
            issue.id
            for issue in issues
            if self._snapshot_is_stale(snapshots.get(issue.id), now=reference_time)
        ]

        if stale_issue_ids:
            for issue_id in stale_issue_ids:
                snapshots[issue_id] = await self.recalculate_issue(issue_id, commit=False)

            if commit:
                await self.session.commit()
            else:
                await self.session.flush()

        return snapshots

    async def recalculate_issue(
        self,
        issue_id: UUID,
        *,
        commit: bool = False,
    ) -> IssueImpactSnapshot:
        issue = await self._load_issue(issue_id)
        snapshot = await self._build_snapshot(issue)
        self.session.add(snapshot)

        if commit:
            await self.session.commit()
            await self.session.refresh(snapshot)
        else:
            await self.session.flush()

        return snapshot

    async def get_public_score(
        self,
        issue_id: UUID,
        *,
        published_only: bool,
    ) -> IssuePublicImpactRead:
        issue = await self._load_issue(issue_id, published_only=published_only)
        snapshots = await self.ensure_issue_metrics([issue], commit=True)
        return self._to_public_read(snapshots[issue.id])

    async def get_admin_breakdown(self, issue_id: UUID) -> IssueImpactAdminRead:
        issue = await self._load_issue(issue_id, published_only=False)
        snapshots = await self.ensure_issue_metrics([issue], commit=True)
        return self._to_admin_read(snapshots[issue.id])

    async def _load_issue(
        self,
        issue_id: UUID,
        *,
        published_only: bool = False,
    ) -> Issue:
        statement = (
            select(Issue)
            .where(Issue.id == issue_id)
            .options(
                selectinload(Issue.author),
                selectinload(Issue.attachments),
                selectinload(Issue.category),
                selectinload(Issue.moderation_results),
                selectinload(Issue.impact_snapshot),
            )
        )
        if published_only:
            statement = statement.where(Issue.status == IssueStatus.PUBLISHED)

        issue = await self.session.scalar(statement)
        if issue is None:
            raise NotFoundError("Issue was not found.")
        return issue

    def _snapshot_is_stale(
        self,
        snapshot: IssueImpactSnapshot | None,
        *,
        now: datetime | None = None,
    ) -> bool:
        if snapshot is None or snapshot.score_version != self.config.score_version:
            return True

        reference_time = now or datetime.now(UTC)
        return ensure_utc(snapshot.updated_at) < reference_time - timedelta(
            minutes=self.config.max_snapshot_age_minutes
        )

    async def _build_snapshot(self, issue: Issue) -> IssueImpactSnapshot:
        support_rows = (
            await self.session.scalars(
                select(SwipeFeedback).where(
                    SwipeFeedback.issue_id == issue.id,
                    SwipeFeedback.direction == SwipeDirection.SUPPORT,
                )
            )
        ).all()
        supporter_ids = {row.user_id for row in support_rows}
        trust_map = await self._load_trust_signals(supporter_ids | {issue.author_id})

        unique_supporters = len(support_rows)
        weighted_support_total = round(
            sum(
                trust_map.get(row.user_id, UserTrustSignal()).weight_multiplier
                for row in support_rows
            ),
            3,
        )
        nearby_related_reports = await self._count_nearby_related_reports(issue)
        duplicate_cluster_size = await self._count_duplicate_cluster(issue.id)
        author_trust_signal = trust_map.get(issue.author_id, UserTrustSignal())
        author_trust_score = author_trust_signal.trust_score
        moderation_confidence = self._moderation_confidence(issue)
        quality_score = self._issue_quality_score(issue)
        moderation_quality_signal = clamp(
            moderation_confidence * 0.65 + quality_score * 0.35
        )
        recency_signal = self._recency_signal(issue)

        weights = self.config.weights
        factor_specs = [
            (
                "unique_supporters",
                "Unique supporters",
                weights.unique_supporters,
                saturating_ratio(unique_supporters, self.config.support_saturation),
                unique_supporters,
                {"saturation_threshold": self.config.support_saturation},
            ),
            (
                "trust_weighted_support",
                "Trust-weighted support",
                weights.trust_weighted_support,
                saturating_ratio(
                    weighted_support_total,
                    self.config.weighted_support_saturation,
                ),
                weighted_support_total,
                {"saturation_threshold": self.config.weighted_support_saturation},
            ),
            (
                "recency",
                "Recency",
                weights.recency,
                recency_signal,
                round(self._days_since(issue.created_at), 2),
                {"half_life_days": self.config.recency_half_life_days},
            ),
            (
                "category_severity",
                "Category severity baseline",
                weights.category_severity,
                clamp(issue.category.severity_baseline),
                issue.category.severity_baseline,
                {},
            ),
            (
                "local_density",
                "Local density of related reports",
                weights.local_density,
                saturating_ratio(
                    nearby_related_reports,
                    self.config.local_density_saturation,
                ),
                nearby_related_reports,
                {
                    "radius_km": self.config.local_density_radius_km,
                    "window_days": self.config.related_report_window_days,
                },
            ),
            (
                "duplicate_aggregation",
                "Duplicate aggregation effect",
                weights.duplicate_aggregation,
                saturating_ratio(
                    duplicate_cluster_size,
                    self.config.duplicate_cluster_saturation,
                ),
                duplicate_cluster_size,
                {"saturation_threshold": self.config.duplicate_cluster_saturation},
            ),
            (
                "moderation_quality",
                "Moderation confidence and report quality",
                weights.moderation_quality,
                moderation_quality_signal,
                round(moderation_confidence, 3),
                {"quality_score": round(quality_score, 3)},
            ),
            (
                "author_trust",
                "Author trust signal",
                weights.author_trust,
                self._normalized_trust(author_trust_score),
                round(author_trust_score, 3),
                {"weight_multiplier": author_trust_signal.weight_multiplier},
            ),
        ]

        factors: list[dict[str, Any]] = []
        score_total = 0.0
        for name, label, weight, signal, raw_value, details in factor_specs:
            contribution = round(weight * signal * 10, 3)
            score_total += contribution
            factors.append(
                {
                    "name": name,
                    "label": label,
                    "weight": round(weight, 3),
                    "signal": round(signal, 3),
                    "contribution": contribution,
                    "raw_value": raw_value,
                    "details": details,
                }
            )

        public_impact_score = round(clamp(score_total, minimum=0.0, maximum=10.0), 1)
        location_assumption, location_multiplier = self._location_type_assumption(
            issue.category.slug
        )
        affected_people_estimate = self._affected_people_estimate(
            issue=issue,
            weighted_support_total=weighted_support_total,
            nearby_related_reports=nearby_related_reports,
            duplicate_cluster_size=duplicate_cluster_size,
            location_multiplier=location_multiplier,
        )

        signals = {
            "unique_supporters": unique_supporters,
            "weighted_support_total": weighted_support_total,
            "nearby_related_reports": nearby_related_reports,
            "duplicate_cluster_size": duplicate_cluster_size,
            "author_trust_score": round(author_trust_score, 3),
            "author_trust_weight_multiplier": author_trust_signal.weight_multiplier,
            "moderation_confidence": round(moderation_confidence, 3),
            "quality_score": round(quality_score, 3),
            "category_severity_baseline": issue.category.severity_baseline,
            "category_affected_people_baseline": issue.category.affected_people_baseline,
            "location_type_assumption": location_assumption,
            "location_multiplier": location_multiplier,
        }
        breakdown = {
            "factors": factors,
            "calculation_notes": [
                "Scores are cached and refreshed when support signals change or snapshots age out.",
                "Affected people is a rounded heuristic, not a census measurement.",
                (
                    "Author trust and moderation confidence are intentionally bounded "
                    "so they do not dominate support and density."
                ),
            ],
        }

        existing_snapshot = issue.impact_snapshot
        if existing_snapshot is None:
            return IssueImpactSnapshot(
                issue_id=issue.id,
                public_impact_score=public_impact_score,
                affected_people_estimate=affected_people_estimate,
                score_version=self.config.score_version,
                signals=signals,
                breakdown=breakdown,
            )

        existing_snapshot.public_impact_score = public_impact_score
        existing_snapshot.affected_people_estimate = affected_people_estimate
        existing_snapshot.score_version = self.config.score_version
        existing_snapshot.signals = signals
        existing_snapshot.breakdown = breakdown
        return existing_snapshot

    async def _load_trust_signals(
        self,
        user_ids: set[UUID],
    ) -> dict[UUID, UserTrustSignal]:
        if not user_ids:
            return {}
        snapshots = await TrustScoreService(self.session).ensure_user_snapshots(
            list(user_ids),
            commit=False,
        )
        return {
            user_id: UserTrustSignal(
                trust_score=snapshot.trust_score,
                weight_multiplier=snapshot.trust_weight_multiplier,
            )
            for user_id, snapshot in snapshots.items()
        }

    def _normalized_trust(self, trust_score: float) -> float:
        return clamp((trust_score - 25) / (95 - 25))

    async def _count_nearby_related_reports(self, issue: Issue) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=self.config.related_report_window_days)
        nearby_candidates = (
            await self.session.scalars(
                select(Issue).where(
                    Issue.id != issue.id,
                    Issue.category_id == issue.category_id,
                    Issue.status.in_(SCORABLE_STATUSES),
                    Issue.created_at >= cutoff,
                )
            )
        ).all()

        return sum(
            1
            for candidate in nearby_candidates
            if distance_km(
                issue.latitude,
                issue.longitude,
                candidate.latitude,
                candidate.longitude,
            )
            <= self.config.local_density_radius_km
        )

    async def _count_duplicate_cluster(self, issue_id: UUID) -> int:
        return int(
            await self.session.scalar(
                select(func.count(IssueDuplicateLink.id)).where(
                    IssueDuplicateLink.canonical_issue_id == issue_id,
                    IssueDuplicateLink.status.in_(
                        (
                            DuplicateResolutionStatus.CONFIRMED,
                            DuplicateResolutionStatus.SUPPORTED_EXISTING,
                        )
                    ),
                )
            )
            or 0
        )

    def _moderation_confidence(self, issue: Issue) -> float:
        if not issue.moderation_results:
            return 0.62 if issue.status == IssueStatus.PUBLISHED else 0.5

        latest_result = max(issue.moderation_results, key=lambda item: item.created_at)
        if latest_result.confidence is None:
            return 0.58
        return clamp(latest_result.confidence)

    def _issue_quality_score(self, issue: Issue) -> float:
        title_length = len(normalize_text(issue.title, max_length=160))
        description_length = len(normalize_text(issue.short_description, max_length=4000))
        title_score = clamp(title_length / 24, minimum=0.25, maximum=1.0)
        description_score = clamp(description_length / 320, maximum=1.0)
        attachment_score = clamp(len(issue.attachments) / 3, maximum=1.0)
        return clamp(
            title_score * 0.35 + description_score * 0.45 + attachment_score * 0.2
        )

    def _recency_signal(self, issue: Issue) -> float:
        age_days = self._days_since(issue.created_at)
        decay = math.exp(
            -math.log(2) * age_days / max(self.config.recency_half_life_days, 1)
        )
        return max(0.2, round(decay, 4))

    @staticmethod
    def _days_since(value: datetime) -> float:
        return max((datetime.now(UTC) - ensure_utc(value)).total_seconds() / 86_400, 0.0)

    def _location_type_assumption(self, category_slug: str) -> tuple[str, float]:
        return self.config.location_type_multipliers.get(
            category_slug,
            ("generic_public_space", 1.0),
        )

    def _affected_people_estimate(
        self,
        *,
        issue: Issue,
        weighted_support_total: float,
        nearby_related_reports: int,
        duplicate_cluster_size: int,
        location_multiplier: float,
    ) -> int:
        base = float(issue.category.affected_people_baseline)
        severity_multiplier = 0.85 + clamp(issue.category.severity_baseline) * 0.65
        raw_estimate = (
            base
            + weighted_support_total * self.config.affected_people_support_multiplier
            + nearby_related_reports * self.config.affected_people_density_multiplier
            + duplicate_cluster_size * self.config.affected_people_duplicate_multiplier
        )
        return round_public_people_estimate(
            raw_estimate * severity_multiplier * location_multiplier
        )

    def importance_label(self, score: float) -> str:
        if score >= 8.5:
            return "High civic priority"
        if score >= 6.5:
            return "Elevated civic priority"
        if score >= 4.5:
            return "Growing civic signal"
        return "Emerging civic signal"

    def _to_public_read(self, snapshot: IssueImpactSnapshot) -> IssuePublicImpactRead:
        return IssuePublicImpactRead(
            issue_id=snapshot.issue_id,
            public_impact_score=snapshot.public_impact_score,
            affected_people_estimate=snapshot.affected_people_estimate,
            importance_label=self.importance_label(snapshot.public_impact_score),
            score_version=snapshot.score_version,
            updated_at=snapshot.updated_at,
        )

    def _to_admin_read(self, snapshot: IssueImpactSnapshot) -> IssueImpactAdminRead:
        return IssueImpactAdminRead(
            issue_id=snapshot.issue_id,
            public_impact_score=snapshot.public_impact_score,
            affected_people_estimate=snapshot.affected_people_estimate,
            importance_label=self.importance_label(snapshot.public_impact_score),
            score_version=snapshot.score_version,
            updated_at=snapshot.updated_at,
            signals=snapshot.signals,
            factors=[
                IssueImpactFactorRead.model_validate(factor)
                for factor in snapshot.breakdown.get("factors", [])
            ],
            calculation_notes=list(snapshot.breakdown.get("calculation_notes", [])),
        )
