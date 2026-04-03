from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models import Issue, IssueCategory, IssueDuplicateLink, SwipeFeedback
from app.models.enums import DuplicateResolutionStatus, IssueStatus, SwipeDirection
from app.schemas.issue import (
    IssueCategoryRead,
    IssueDuplicateSuggestionRequest,
    IssueDuplicateSuggestionResponse,
    IssueFeedbackRead,
    IssueRewriteRequest,
    IssueRewriteResponse,
    IssueSupportExistingRead,
    IssueSupportExistingRequest,
    PublicIssueDetailRead,
    PublicIssueMapMarkerRead,
    PublicIssueSummaryRead,
)
from app.services.ai_rewrite import AIRewriteService
from app.services.duplicate_detection import DuplicateDetectionService
from app.services.impact_scores import ImpactScoreService
from app.services.intelligence_utils import distance_km, normalize_text


@dataclass(slots=True)
class PublicIssueQuery:
    sort: str = "recent"
    category_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    limit: int = 24
    exclude_issue_ids: tuple[UUID, ...] = ()


class PublicIssueService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.impact_scores = ImpactScoreService(session)
        self.duplicate_detection = DuplicateDetectionService(session)
        self.ai_rewrite = AIRewriteService()

    async def list_categories(self) -> list[IssueCategoryRead]:
        categories = await self.session.scalars(
            select(IssueCategory)
            .where(IssueCategory.is_active.is_(True))
            .order_by(IssueCategory.display_name.asc())
        )
        return [IssueCategoryRead.model_validate(category) for category in categories.all()]

    async def list_public_issues(
        self,
        query: PublicIssueQuery,
    ) -> list[PublicIssueSummaryRead]:
        issues = await self._load_public_issues(query)
        snapshots = await self.impact_scores.ensure_issue_metrics(issues, commit=True)
        sorted_issues = self._sort_issues(issues, snapshots, query)

        return [
            self._to_public_summary(issue, snapshots.get(issue.id), query)
            for issue in sorted_issues[: query.limit]
        ]

    async def list_public_map_markers(
        self,
        query: PublicIssueQuery,
    ) -> list[PublicIssueMapMarkerRead]:
        issues = await self._load_public_issues(query)
        snapshots = await self.impact_scores.ensure_issue_metrics(issues, commit=True)
        sorted_issues = self._sort_issues(issues, snapshots, query)

        return [
            self._to_public_map_marker(issue, snapshots.get(issue.id))
            for issue in sorted_issues[: query.limit]
        ]

    async def get_public_issue(self, issue_id: UUID) -> PublicIssueDetailRead:
        issue = await self.session.scalar(
            select(Issue)
            .where(Issue.id == issue_id, Issue.status == IssueStatus.PUBLISHED)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.impact_snapshot),
            )
        )
        if issue is None:
            raise NotFoundError("Public issue was not found.")

        snapshots = await self.impact_scores.ensure_issue_metrics([issue], commit=True)
        return self._to_public_detail(issue, snapshots.get(issue.id))

    async def suggest_duplicates(
        self,
        payload: IssueDuplicateSuggestionRequest,
    ) -> IssueDuplicateSuggestionResponse:
        return await self.duplicate_detection.find_duplicate_candidates(payload)

    async def rewrite_issue_text(
        self,
        payload: IssueRewriteRequest,
    ) -> IssueRewriteResponse:
        category_slug = None
        if payload.category_id is not None:
            category = await self.session.scalar(
                select(IssueCategory).where(IssueCategory.id == payload.category_id)
            )
            category_slug = category.slug if category else None

        response = await self.ai_rewrite.rewrite(payload, category_slug=category_slug)
        return IssueRewriteResponse(
            rewritten_title=normalize_text(response.rewritten_title, max_length=160),
            rewritten_description=normalize_text(
                response.rewritten_description,
                max_length=4000,
            ),
            explanation=response.explanation,
            tone_classification=response.tone_classification,
        )

    async def record_feedback(
        self,
        *,
        issue_id: UUID,
        user_id: UUID,
        action: SwipeDirection,
    ) -> IssueFeedbackRead:
        issue = await self._load_public_issue_for_feedback(issue_id)
        feedback, support_changed = await self._upsert_feedback(
            issue_id=issue.id,
            user_id=user_id,
            action=action,
        )
        await self.session.flush()
        snapshot = await self.impact_scores.recalculate_issue(issue.id, commit=False)
        await self.session.commit()

        return IssueFeedbackRead(
            issue_id=issue.id,
            action=feedback.direction,
            support_count=int(snapshot.signals.get("unique_supporters", 0)),
            support_changed=support_changed,
            public_impact_score=snapshot.public_impact_score,
            affected_people_estimate=snapshot.affected_people_estimate,
        )

    async def support_existing_issue(
        self,
        *,
        issue_id: UUID,
        user_id: UUID,
        payload: IssueSupportExistingRequest,
    ) -> IssueSupportExistingRead:
        issue = await self._load_public_issue_for_feedback(issue_id)
        _, support_changed = await self._upsert_feedback(
            issue_id=issue.id,
            user_id=user_id,
            action=SwipeDirection.SUPPORT,
        )

        duplicate_link = None
        if self._should_capture_duplicate_signal(payload):
            duplicate_link = IssueDuplicateLink(
                canonical_issue_id=issue.id,
                created_by_user_id=user_id,
                status=DuplicateResolutionStatus.SUPPORTED_EXISTING,
                similarity_score=payload.similarity_score,
                distance_km=payload.distance_km,
                text_similarity=payload.text_similarity,
                category_match=payload.category_match,
                reason_breakdown={"reasons": payload.reason_breakdown},
                candidate_snapshot={
                    "title": payload.candidate_title,
                    "short_description": payload.candidate_description,
                    "category_id": str(payload.candidate_category_id)
                    if payload.candidate_category_id
                    else None,
                    "latitude": payload.candidate_latitude,
                    "longitude": payload.candidate_longitude,
                    "image_hashes": payload.image_hashes,
                },
            )
            self.session.add(duplicate_link)

        await self.session.flush()
        snapshot = await self.impact_scores.recalculate_issue(issue.id, commit=False)
        await self.session.commit()

        return IssueSupportExistingRead(
            canonical_issue_id=issue.id,
            duplicate_link_id=duplicate_link.id if duplicate_link else None,
            support_count=int(snapshot.signals.get("unique_supporters", 0)),
            support_changed=support_changed,
            public_impact_score=snapshot.public_impact_score,
            affected_people_estimate=snapshot.affected_people_estimate,
        )

    async def _load_public_issues(self, query: PublicIssueQuery) -> list[Issue]:
        statement = (
            select(Issue)
            .where(Issue.status == IssueStatus.PUBLISHED)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.impact_snapshot),
            )
        )

        if query.category_id is not None:
            statement = statement.where(Issue.category_id == query.category_id)

        if query.exclude_issue_ids:
            statement = statement.where(Issue.id.not_in(query.exclude_issue_ids))

        issues = await self.session.scalars(statement)
        return list(issues.all())

    async def _load_public_issue_for_feedback(self, issue_id: UUID) -> Issue:
        issue = await self.session.scalar(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.status == IssueStatus.PUBLISHED,
            )
        )
        if issue is None:
            raise NotFoundError("Public issue was not found.")
        return issue

    async def _upsert_feedback(
        self,
        *,
        issue_id: UUID,
        user_id: UUID,
        action: SwipeDirection,
    ) -> tuple[SwipeFeedback, bool]:
        feedback = await self.session.scalar(
            select(SwipeFeedback).where(
                SwipeFeedback.user_id == user_id,
                SwipeFeedback.issue_id == issue_id,
            )
        )
        was_support = feedback is not None and feedback.direction == SwipeDirection.SUPPORT

        if feedback is None:
            feedback = SwipeFeedback(
                user_id=user_id,
                issue_id=issue_id,
                direction=action,
            )
            self.session.add(feedback)
        else:
            feedback.direction = action

        support_changed = action == SwipeDirection.SUPPORT and not was_support
        return feedback, support_changed

    def _sort_issues(self, issues, snapshots, query: PublicIssueQuery):
        if query.sort == "top":
            return sorted(
                issues,
                key=lambda issue: (
                    snapshots.get(issue.id).public_impact_score if snapshots.get(issue.id) else 0,
                    issue.created_at,
                ),
                reverse=True,
            )

        if query.sort == "nearby" and query.latitude is not None and query.longitude is not None:
            return sorted(
                issues,
                key=lambda issue: distance_km(
                    query.latitude,
                    query.longitude,
                    issue.latitude,
                    issue.longitude,
                ),
            )

        return sorted(issues, key=lambda issue: issue.created_at, reverse=True)

    def _to_public_summary(
        self,
        issue: Issue,
        snapshot,
        query: PublicIssueQuery | None = None,
    ) -> PublicIssueSummaryRead:
        distance_value = None
        if query is not None and query.latitude is not None and query.longitude is not None:
            distance_value = round(
                distance_km(
                    query.latitude,
                    query.longitude,
                    issue.latitude,
                    issue.longitude,
                ),
                2,
            )

        return PublicIssueSummaryRead(
            id=issue.id,
            title=issue.title,
            short_description=issue.short_description,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=IssueCategoryRead.model_validate(issue.category),
            location_snippet=self._location_snippet(issue),
            support_count=int(snapshot.signals.get("unique_supporters", 0)) if snapshot else 0,
            public_impact_score=snapshot.public_impact_score if snapshot else None,
            affected_people_estimate=(
                snapshot.affected_people_estimate if snapshot else None
            ),
            importance_label=(
                self.impact_scores.importance_label(snapshot.public_impact_score)
                if snapshot
                else None
            ),
            cover_image_url=self._cover_image_url(issue),
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            distance_km=distance_value,
        )

    def _to_public_detail(self, issue: Issue, snapshot) -> PublicIssueDetailRead:
        return PublicIssueDetailRead(
            id=issue.id,
            title=issue.title,
            short_description=issue.short_description,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=IssueCategoryRead.model_validate(issue.category),
            location_snippet=self._location_snippet(issue),
            support_count=int(snapshot.signals.get("unique_supporters", 0)) if snapshot else 0,
            public_impact_score=snapshot.public_impact_score if snapshot else None,
            affected_people_estimate=(
                snapshot.affected_people_estimate if snapshot else None
            ),
            importance_label=(
                self.impact_scores.importance_label(snapshot.public_impact_score)
                if snapshot
                else None
            ),
            cover_image_url=self._cover_image_url(issue),
            source_locale=issue.source_locale,
            attachments=[attachment for attachment in issue.attachments],
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    def _to_public_map_marker(self, issue: Issue, snapshot) -> PublicIssueMapMarkerRead:
        return PublicIssueMapMarkerRead(
            id=issue.id,
            title=issue.title,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=IssueCategoryRead.model_validate(issue.category),
            location_snippet=self._location_snippet(issue),
            support_count=int(snapshot.signals.get("unique_supporters", 0)) if snapshot else 0,
            public_impact_score=snapshot.public_impact_score if snapshot else None,
            affected_people_estimate=(
                snapshot.affected_people_estimate if snapshot else None
            ),
            importance_label=(
                self.impact_scores.importance_label(snapshot.public_impact_score)
                if snapshot
                else None
            ),
        )

    def _cover_image_url(self, issue: Issue) -> str | None:
        if not issue.attachments:
            return None

        first_attachment = issue.attachments[0]
        if not self.settings.s3_endpoint_url:
            return None

        endpoint = self.settings.s3_endpoint_url.rstrip("/")
        return f"{endpoint}/{self.settings.s3_bucket}/{first_attachment.storage_key}"

    @staticmethod
    def _location_snippet(issue: Issue) -> str:
        return f"{issue.latitude:.3f}, {issue.longitude:.3f}"

    @staticmethod
    def _should_capture_duplicate_signal(payload: IssueSupportExistingRequest) -> bool:
        return any(
            value
            for value in (
                payload.candidate_title,
                payload.candidate_description,
                payload.candidate_category_id,
                payload.candidate_latitude,
                payload.candidate_longitude,
                payload.similarity_score,
                payload.distance_km,
                payload.text_similarity,
                payload.reason_breakdown,
                payload.image_hashes,
            )
        )
