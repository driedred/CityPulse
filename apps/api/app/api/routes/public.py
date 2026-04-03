from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.issue import (
    IssueCategoryRead,
    IssueDuplicateSuggestionRequest,
    IssueDuplicateSuggestionResponse,
    IssueFeedbackCreate,
    IssueFeedbackRead,
    IssuePublicImpactRead,
    IssueRewriteRequest,
    IssueRewriteResponse,
    IssueSupportExistingRead,
    IssueSupportExistingRequest,
    PublicIssueDetailRead,
    PublicIssueMapMarkerRead,
    PublicIssueSummaryRead,
)
from app.services.public_issues import PublicIssueQuery, PublicIssueService

router = APIRouter(prefix="/public", tags=["public-issues"])


@router.get("/categories", response_model=list[IssueCategoryRead])
async def list_issue_categories(session: SessionDep) -> list[IssueCategoryRead]:
    service = PublicIssueService(session)
    return await service.list_categories()


@router.get("/issues/feed", response_model=list[PublicIssueSummaryRead])
async def list_public_issue_feed(
    session: SessionDep,
    sort: str = "recent",
    category_id: UUID | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 12,
    exclude_issue_ids: Annotated[list[UUID] | None, Query()] = None,
) -> list[PublicIssueSummaryRead]:
    service = PublicIssueService(session)
    return await service.list_public_issues(
        PublicIssueQuery(
            sort=sort,
            category_id=category_id,
            latitude=latitude,
            longitude=longitude,
            limit=min(limit, 30),
            exclude_issue_ids=tuple(exclude_issue_ids or []),
        )
    )


@router.get("/issues", response_model=list[PublicIssueSummaryRead])
async def list_public_issues(
    session: SessionDep,
    sort: str = "recent",
    category_id: UUID | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 24,
) -> list[PublicIssueSummaryRead]:
    service = PublicIssueService(session)
    return await service.list_public_issues(
        PublicIssueQuery(
            sort=sort,
            category_id=category_id,
            latitude=latitude,
            longitude=longitude,
            limit=min(limit, 60),
        )
    )


@router.get("/issues/map", response_model=list[PublicIssueMapMarkerRead])
async def list_public_issue_map_markers(
    session: SessionDep,
    category_id: UUID | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 80,
) -> list[PublicIssueMapMarkerRead]:
    service = PublicIssueService(session)
    return await service.list_public_map_markers(
        PublicIssueQuery(
            sort="recent",
            category_id=category_id,
            latitude=latitude,
            longitude=longitude,
            limit=min(limit, 120),
        )
    )


@router.get("/issues/{issue_id}", response_model=PublicIssueDetailRead)
async def get_public_issue(
    issue_id: UUID,
    session: SessionDep,
) -> PublicIssueDetailRead:
    service = PublicIssueService(session)
    return await service.get_public_issue(issue_id)


@router.get("/issues/{issue_id}/impact", response_model=IssuePublicImpactRead)
async def get_public_issue_impact(
    issue_id: UUID,
    session: SessionDep,
) -> IssuePublicImpactRead:
    service = PublicIssueService(session)
    return await service.impact_scores.get_public_score(issue_id, published_only=True)


@router.post(
    "/issues/duplicates",
    response_model=IssueDuplicateSuggestionResponse,
    status_code=status.HTTP_200_OK,
)
async def suggest_issue_duplicates(
    payload: IssueDuplicateSuggestionRequest,
    session: SessionDep,
) -> IssueDuplicateSuggestionResponse:
    service = PublicIssueService(session)
    return await service.suggest_duplicates(payload)


@router.post("/issues/rewrite", response_model=IssueRewriteResponse)
async def rewrite_issue_text(
    payload: IssueRewriteRequest,
    session: SessionDep,
) -> IssueRewriteResponse:
    service = PublicIssueService(session)
    return await service.rewrite_issue_text(payload)


@router.post("/issues/{issue_id}/feedback", response_model=IssueFeedbackRead)
async def record_issue_feedback(
    issue_id: UUID,
    payload: IssueFeedbackCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> IssueFeedbackRead:
    service = PublicIssueService(session)
    return await service.record_feedback(
        issue_id=issue_id,
        user_id=current_user.id,
        action=payload.action,
    )


@router.post("/issues/{issue_id}/support", response_model=IssueSupportExistingRead)
async def support_existing_issue(
    issue_id: UUID,
    payload: IssueSupportExistingRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> IssueSupportExistingRead:
    service = PublicIssueService(session)
    return await service.support_existing_issue(
        issue_id=issue_id,
        user_id=current_user.id,
        payload=payload,
    )
