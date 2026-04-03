from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.issue import (
    AdminModerationIssueRead,
    IssueCategoryRead,
    IssueModerationAuditRead,
)
from app.services.moderation import ModerationPipelineService, serialize_moderation_result_user


class AdminModerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.pipeline = ModerationPipelineService(session)

    async def list_recent_issues(self, *, limit: int = 30) -> list[AdminModerationIssueRead]:
        issues = await self.pipeline.list_issue_audits(limit=limit)
        return [
            AdminModerationIssueRead(
                id=issue.id,
                title=issue.title,
                short_description=issue.short_description,
                source_locale=issue.source_locale,
                status=issue.status,
                moderation_state=issue.moderation_state,
                category=IssueCategoryRead.model_validate(issue.category),
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                attachment_count=len(issue.attachments),
                latest_moderation=serialize_moderation_result_user(issue.latest_moderation_result),
            )
            for issue in issues
        ]

    async def get_issue_detail(self, issue_id: UUID) -> IssueModerationAuditRead:
        return await self.pipeline.get_issue_audit(issue_id)

    async def rerun_issue(self, issue_id: UUID) -> IssueModerationAuditRead:
        await self.pipeline.moderate_issue(issue_id)
        return await self.pipeline.get_issue_audit(issue_id)
