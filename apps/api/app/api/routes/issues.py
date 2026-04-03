from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, SessionDep, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.issue import (
    IssueAttachmentCreate,
    IssueAttachmentRead,
    IssueCreate,
    IssueImpactAdminRead,
    IssuePublicImpactRead,
    IssueRead,
)
from app.services.impact_scores import ImpactScoreService
from app.services.issues import IssueService
from app.services.moderation import LogOnlyModerationDispatcher

router = APIRouter(prefix="/issues", tags=["issues"])
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.post("", response_model=IssueRead, status_code=status.HTTP_201_CREATED)
async def submit_issue(
    payload: IssueCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> IssueRead:
    service = IssueService(session, LogOnlyModerationDispatcher())
    issue = await service.create_issue(current_user, payload)
    return IssueRead.model_validate(issue)


@router.post(
    "/{issue_id}/attachments",
    response_model=IssueAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue_attachment_metadata(
    issue_id: UUID,
    payload: IssueAttachmentCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> IssueAttachmentRead:
    service = IssueService(session, LogOnlyModerationDispatcher())
    attachment = await service.create_attachment_metadata(issue_id, current_user, payload)
    return IssueAttachmentRead.model_validate(attachment)


@router.get("/me", response_model=list[IssueRead])
async def list_own_issues(
    current_user: CurrentUser,
    session: SessionDep,
) -> list[IssueRead]:
    service = IssueService(session, LogOnlyModerationDispatcher())
    issues = await service.list_user_issues(current_user)
    return [IssueRead.model_validate(issue) for issue in issues]


@router.get("/{issue_id}/impact", response_model=IssuePublicImpactRead)
async def get_issue_public_impact(
    issue_id: UUID,
    current_user: CurrentUser,
    session: SessionDep,
) -> IssuePublicImpactRead:
    del current_user
    return await ImpactScoreService(session).get_public_score(
        issue_id,
        published_only=False,
    )


@router.get("/{issue_id}/impact/admin", response_model=IssueImpactAdminRead)
async def get_issue_admin_impact(
    issue_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> IssueImpactAdminRead:
    del admin_user
    return await ImpactScoreService(session).get_admin_breakdown(issue_id)


@router.post("/{issue_id}/impact/recalculate", response_model=IssueImpactAdminRead)
async def recalculate_issue_impact(
    issue_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> IssueImpactAdminRead:
    del admin_user
    service = ImpactScoreService(session)
    await service.recalculate_issue(issue_id, commit=True)
    return await service.get_admin_breakdown(issue_id)
