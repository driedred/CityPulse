from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models import Issue, IssueCategory, ModerationResult
from app.models.enums import (
    IssueStatus,
    ModerationLayer,
    ModerationResultStatus,
    ModerationState,
)
from app.schemas.issue import (
    IssueModerationAdminRead,
    IssueModerationAuditRead,
    IssueModerationUserRead,
    ModerationReasonRead,
)
from app.services.deterministic_moderation import DeterministicModerationService
from app.services.llm_moderation import LLMModerationService
from app.services.moderation_models import (
    ModerationAttachmentDescriptor,
    ModerationSubmission,
)


class ModerationDispatcher(Protocol):
    async def enqueue_issue(self, issue_id: UUID) -> None:
        ...


class ModerationPipelineService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        deterministic_service: DeterministicModerationService | None = None,
        llm_service: LLMModerationService | None = None,
    ) -> None:
        self.session = session
        self.deterministic_service = deterministic_service or DeterministicModerationService()
        self.llm_service = llm_service or LLMModerationService()

    async def moderate_issue(self, issue_id: UUID) -> Issue:
        issue = await self._load_issue(issue_id)
        submission = self._to_submission(issue)
        allowed_category_slugs = await self._load_allowed_category_slugs()

        deterministic_decision = self.deterministic_service.evaluate(submission)
        deterministic_result = ModerationResult(
            issue_id=issue.id,
            status=self._status_from_decision(deterministic_decision.outcome),
            layer=ModerationLayer.DETERMINISTIC,
            decision_code=deterministic_decision.outcome,
            provider_name="citypulse-deterministic",
            model_name="rule-engine-v1",
            machine_reasons=[
                reason.model_dump(mode="json") for reason in deterministic_decision.machine_reasons
            ],
            user_safe_explanation=deterministic_decision.user_safe_explanation,
            internal_notes=deterministic_decision.internal_notes,
            escalation_required=deterministic_decision.escalation_required,
            flags=deterministic_decision.flags,
            confidence=deterministic_decision.confidence,
            summary=deterministic_decision.summary,
        )
        self.session.add(deterministic_result)

        if deterministic_decision.outcome == "reject":
            self._apply_issue_decision(issue, deterministic_result.status)
            await self.session.commit()
            await self.session.refresh(issue)
            return issue

        llm_decision = await self.llm_service.review(
            submission,
            deterministic_decision,
            allowed_category_slugs=allowed_category_slugs,
        )
        llm_result = ModerationResult(
            issue_id=issue.id,
            status=self._status_from_decision(llm_decision.outcome),
            layer=ModerationLayer.LLM,
            decision_code=llm_decision.outcome,
            provider_name=(
                "openai"
                if not llm_decision.flags.get("fallback")
                else "citypulse-fallback"
            ),
            model_name=(
                self.llm_service.client.settings.openai_model
                if not llm_decision.flags.get("fallback")
                else "local-contextual"
            ),
            machine_reasons=[
                reason.model_dump(mode="json") for reason in llm_decision.machine_reasons
            ],
            user_safe_explanation=llm_decision.user_safe_explanation,
            internal_notes=llm_decision.internal_notes,
            escalation_required=llm_decision.escalation_required,
            normalized_category_slug=llm_decision.normalized_category_slug,
            flags=llm_decision.flags,
            confidence=llm_decision.confidence,
            summary=llm_decision.summary,
        )
        self.session.add(llm_result)
        self._apply_issue_decision(issue, llm_result.status)
        await self.session.commit()
        await self.session.refresh(issue)
        return issue

    async def get_issue_audit(self, issue_id: UUID) -> IssueModerationAuditRead:
        issue = await self._load_issue(issue_id)
        latest_result = issue.latest_moderation_result
        return IssueModerationAuditRead(
            issue_id=issue.id,
            issue_status=issue.status,
            moderation_state=issue.moderation_state,
            latest_result=serialize_moderation_result_user(latest_result),
            results=[
                serialize_moderation_result_admin(result)
                for result in sorted(issue.moderation_results, key=lambda item: item.created_at)
            ],
        )

    async def list_issue_audits(
        self,
        *,
        limit: int = 30,
    ) -> list[Issue]:
        issues = await self.session.scalars(
            select(Issue)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.moderation_results),
            )
            .order_by(Issue.created_at.desc())
            .limit(limit)
        )
        return list(issues.all())

    async def _load_issue(self, issue_id: UUID) -> Issue:
        issue = await self.session.scalar(
            select(Issue)
            .where(Issue.id == issue_id)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.moderation_results),
            )
        )
        if issue is None:
            raise NotFoundError("Issue was not found.")
        return issue

    async def _load_allowed_category_slugs(self) -> set[str]:
        categories = await self.session.scalars(
            select(IssueCategory.slug).where(IssueCategory.is_active.is_(True))
        )
        return set(categories.all())

    @staticmethod
    def _to_submission(issue: Issue) -> ModerationSubmission:
        return ModerationSubmission(
            issue_id=issue.id,
            author_id=issue.author_id,
            title=issue.title,
            short_description=issue.short_description,
            category_slug=issue.category.slug,
            source_locale=issue.source_locale,
            latitude=issue.latitude,
            longitude=issue.longitude,
            attachments=tuple(
                ModerationAttachmentDescriptor(
                    original_filename=attachment.original_filename,
                    content_type=attachment.content_type,
                    size_bytes=attachment.size_bytes,
                )
                for attachment in issue.attachments
            ),
        )

    @staticmethod
    def _status_from_decision(decision: str) -> ModerationResultStatus:
        if decision in {"pass", "approve"}:
            return ModerationResultStatus.APPROVED
        if decision == "reject":
            return ModerationResultStatus.REJECTED
        return ModerationResultStatus.NEEDS_REVIEW

    @staticmethod
    def _apply_issue_decision(issue: Issue, status: ModerationResultStatus) -> None:
        if status == ModerationResultStatus.REJECTED:
            issue.status = IssueStatus.REJECTED
            issue.moderation_state = ModerationState.COMPLETED
            return

        if status == ModerationResultStatus.NEEDS_REVIEW:
            issue.status = IssueStatus.PENDING_MODERATION
            issue.moderation_state = ModerationState.UNDER_REVIEW
            return

        if issue.status != IssueStatus.PUBLISHED:
            issue.status = IssueStatus.APPROVED
        issue.moderation_state = ModerationState.COMPLETED


class InlineModerationDispatcher:
    def __init__(self, session: AsyncSession) -> None:
        self.pipeline = ModerationPipelineService(session)

    async def enqueue_issue(self, issue_id: UUID) -> None:
        await self.pipeline.moderate_issue(issue_id)


def _deserialize_reasons(value: Iterable[dict] | None) -> list[ModerationReasonRead]:
    if not value:
        return []
    return [ModerationReasonRead.model_validate(item) for item in value]


def serialize_moderation_result_user(
    result: ModerationResult | None,
) -> IssueModerationUserRead | None:
    if result is None:
        return None
    return IssueModerationUserRead(
        id=result.id,
        layer=result.layer,
        status=result.status,
        decision_code=result.decision_code,
        provider_name=result.provider_name,
        model_name=result.model_name,
        confidence=result.confidence,
        summary=result.summary,
        user_safe_explanation=result.user_safe_explanation,
        escalation_required=result.escalation_required,
        machine_reasons=_deserialize_reasons(result.machine_reasons),
        normalized_category_slug=result.normalized_category_slug,
        created_at=result.created_at,
    )


def serialize_moderation_result_admin(result: ModerationResult) -> IssueModerationAdminRead:
    return IssueModerationAdminRead(
        **serialize_moderation_result_user(result).model_dump(),
        internal_notes=result.internal_notes,
        flags=result.flags,
    )
