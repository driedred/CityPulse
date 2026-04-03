from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.issue import (
    IssueAttachmentCreate,
    IssueAttachmentRead,
    IssueCreate,
    IssueRead,
)
from app.services.issues import IssueService
from app.services.moderation import LogOnlyModerationDispatcher

router = APIRouter(prefix="/issues", tags=["issues"])


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
