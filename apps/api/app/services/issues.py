from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models import Issue, IssueAttachment, IssueCategory, User
from app.models.enums import IssueStatus, ModerationState, UserRole
from app.schemas.issue import (
    IssueAttachmentCreate,
    IssueAttachmentRead,
    IssueCategoryRead,
    IssueCreate,
    IssueRead,
)
from app.services.anti_abuse import AntiAbuseService
from app.services.moderation import ModerationDispatcher, serialize_moderation_result_user
from app.services.trust_scores import TrustScoreService


class IssueService:
    def __init__(
        self,
        session: AsyncSession,
        moderation_dispatcher: ModerationDispatcher,
    ) -> None:
        self.session = session
        self.moderation_dispatcher = moderation_dispatcher
        self.anti_abuse = AntiAbuseService(session)
        self.trust_scores = TrustScoreService(session)

    async def create_issue(self, author: User, payload: IssueCreate) -> Issue:
        duplicate_result = await self.anti_abuse.guard_issue_submission(
            user=author,
            payload=payload,
        )
        category = await self.session.scalar(
            select(IssueCategory).where(
                IssueCategory.id == payload.category_id,
                IssueCategory.is_active.is_(True),
            )
        )
        if category is None:
            raise NotFoundError("Issue category was not found.")

        issue = Issue(
            author_id=author.id,
            category_id=payload.category_id,
            title=payload.title.strip(),
            short_description=payload.short_description.strip(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            source_locale=payload.source_locale,
            status=IssueStatus.PENDING_MODERATION,
            moderation_state=ModerationState.QUEUED,
        )

        self.session.add(issue)
        await self.session.commit()
        await self.moderation_dispatcher.enqueue_issue(issue.id)
        issue = await self.get_issue(issue.id)
        await self.anti_abuse.record_issue_submission_created(
            user=author,
            issue=issue,
            duplicate_status=duplicate_result.status if duplicate_result else None,
        )
        await self.trust_scores.recalculate_user(author.id, commit=True)
        return await self.get_issue(issue.id)

    async def create_attachment_metadata(
        self,
        issue_id,
        actor: User,
        payload: IssueAttachmentCreate,
    ) -> IssueAttachment:
        issue = await self.session.scalar(select(Issue).where(Issue.id == issue_id))
        if issue is None:
            raise NotFoundError("Issue was not found.")

        if actor.role != UserRole.ADMIN and issue.author_id != actor.id:
            raise AuthorizationError(
                "You can only attach metadata to issues that you created."
            )

        existing_attachment = await self.session.scalar(
            select(IssueAttachment).where(IssueAttachment.storage_key == payload.storage_key)
        )
        if existing_attachment is not None:
            raise ConflictError("That storage key is already registered.")

        attachment = IssueAttachment(
            issue_id=issue.id,
            uploader_id=actor.id,
            storage_key=payload.storage_key,
            original_filename=payload.original_filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            moderation_image_url=payload.moderation_image_url,
        )
        self.session.add(attachment)
        await self.session.commit()
        await self.moderation_dispatcher.enqueue_issue(issue.id)
        await self.session.refresh(attachment)
        return attachment

    async def list_user_issues(self, actor: User) -> list[Issue]:
        result = await self.session.scalars(
            select(Issue)
            .where(Issue.author_id == actor.id)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.impact_snapshot),
                selectinload(Issue.moderation_results),
            )
            .order_by(Issue.created_at.desc())
        )
        return list(result.all())

    async def get_issue(self, issue_id) -> Issue:
        issue = await self.session.scalar(
            select(Issue)
            .where(Issue.id == issue_id)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
                selectinload(Issue.impact_snapshot),
                selectinload(Issue.moderation_results),
            )
        )
        if issue is None:
            raise NotFoundError("Issue was not found.")
        return issue

    async def get_issue_for_actor(self, issue_id, actor: User) -> Issue:
        issue = await self.get_issue(issue_id)
        if actor.role != UserRole.ADMIN and issue.author_id != actor.id:
            raise AuthorizationError("You do not have access to this issue.")
        return issue

    @staticmethod
    def serialize_issue(issue: Issue) -> IssueRead:
        snapshot = issue.impact_snapshot
        support_count = int(snapshot.signals.get("unique_supporters", 0)) if snapshot else 0
        return IssueRead(
            id=issue.id,
            author_id=issue.author_id,
            title=issue.title,
            short_description=issue.short_description,
            latitude=issue.latitude,
            longitude=issue.longitude,
            status=issue.status,
            moderation_state=issue.moderation_state,
            source_locale=issue.source_locale,
            category=IssueCategoryRead.model_validate(issue.category),
            attachments=[
                IssueAttachmentRead.model_validate(attachment)
                for attachment in issue.attachments
            ],
            support_count=support_count,
            location_snippet=f"{issue.latitude:.3f}, {issue.longitude:.3f}",
            public_impact_score=snapshot.public_impact_score if snapshot else None,
            affected_people_estimate=(
                snapshot.affected_people_estimate if snapshot else None
            ),
            latest_moderation=serialize_moderation_result_user(issue.latest_moderation_result),
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )
