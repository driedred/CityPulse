from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models import Issue, IssueAttachment, IssueCategory, User
from app.models.enums import IssueStatus, ModerationState, UserRole
from app.schemas.issue import IssueAttachmentCreate, IssueCreate
from app.services.moderation import ModerationDispatcher


class IssueService:
    def __init__(
        self,
        session: AsyncSession,
        moderation_dispatcher: ModerationDispatcher,
    ) -> None:
        self.session = session
        self.moderation_dispatcher = moderation_dispatcher

    async def create_issue(self, author: User, payload: IssueCreate) -> Issue:
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
        )
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment

    async def list_user_issues(self, actor: User) -> list[Issue]:
        result = await self.session.scalars(
            select(Issue)
            .where(Issue.author_id == actor.id)
            .options(
                selectinload(Issue.category),
                selectinload(Issue.attachments),
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
            )
        )
        if issue is None:
            raise NotFoundError("Issue was not found.")
        return issue
