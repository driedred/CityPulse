from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.issue import AdminModerationIssueRead, IssueModerationAuditRead
from app.schemas.user import UserIntegrityDetailRead, UserIntegritySummaryRead
from app.services.admin_integrity import AdminIntegrityService
from app.services.admin_moderation import AdminModerationService

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/moderation/issues", response_model=list[AdminModerationIssueRead])
async def list_recent_moderation_issues(
    admin_user: AdminUser,
    session: SessionDep,
    limit: int = 30,
) -> list[AdminModerationIssueRead]:
    del admin_user
    return await AdminModerationService(session).list_recent_issues(limit=min(limit, 60))


@router.get(
    "/moderation/issues/{issue_id}",
    response_model=IssueModerationAuditRead,
)
async def get_moderation_issue_detail(
    issue_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> IssueModerationAuditRead:
    del admin_user
    return await AdminModerationService(session).get_issue_detail(issue_id)


@router.post(
    "/moderation/issues/{issue_id}/rerun",
    response_model=IssueModerationAuditRead,
)
async def rerun_issue_moderation(
    issue_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> IssueModerationAuditRead:
    del admin_user
    return await AdminModerationService(session).rerun_issue(issue_id)


@router.get("/users", response_model=list[UserIntegritySummaryRead])
async def list_integrity_users(
    admin_user: AdminUser,
    session: SessionDep,
    limit: int = 40,
) -> list[UserIntegritySummaryRead]:
    del admin_user
    return await AdminIntegrityService(session).list_users(limit=min(limit, 80))


@router.get("/users/{user_id}/integrity", response_model=UserIntegrityDetailRead)
async def get_user_integrity_detail(
    user_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> UserIntegrityDetailRead:
    del admin_user
    return await AdminIntegrityService(session).get_user_detail(user_id)


@router.post("/users/{user_id}/integrity/recalculate", response_model=UserIntegrityDetailRead)
async def recalculate_user_integrity(
    user_id: UUID,
    admin_user: AdminUser,
    session: SessionDep,
) -> UserIntegrityDetailRead:
    del admin_user
    return await AdminIntegrityService(session).recalculate_user(user_id)
