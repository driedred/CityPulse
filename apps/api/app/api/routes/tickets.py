from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.support_ticket import SupportTicketCreate, SupportTicketRead
from app.services.support_tickets import SupportTicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=SupportTicketRead, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    payload: SupportTicketCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> SupportTicketRead:
    service = SupportTicketService(session)
    ticket = await service.create_ticket(current_user, payload)
    return SupportTicketRead.model_validate(ticket)


@router.get("/me", response_model=list[SupportTicketRead])
async def list_own_tickets(
    current_user: CurrentUser,
    session: SessionDep,
) -> list[SupportTicketRead]:
    service = SupportTicketService(session)
    tickets = await service.list_user_tickets(current_user)
    return [SupportTicketRead.model_validate(ticket) for ticket in tickets]
