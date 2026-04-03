from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, NotFoundError
from app.models import Issue, SupportTicket, TicketMessage, User
from app.models.enums import SupportTicketStatus, UserRole
from app.schemas.support_ticket import SupportTicketCreate


class SupportTicketService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_ticket(self, author: User, payload: SupportTicketCreate) -> SupportTicket:
        issue_id = payload.issue_id

        if issue_id is not None:
            issue = await self.session.scalar(select(Issue).where(Issue.id == issue_id))
            if issue is None:
                raise NotFoundError("Referenced issue was not found.")
            if author.role != UserRole.ADMIN and issue.author_id != author.id:
                raise AuthorizationError(
                    "You can only open support tickets for your own issues."
                )

        ticket = SupportTicket(
            issue_id=issue_id,
            author_id=author.id,
            ticket_type=payload.ticket_type,
            status=SupportTicketStatus.OPEN,
            subject=payload.subject.strip(),
        )
        ticket.messages.append(
            TicketMessage(
                author_id=author.id,
                body=payload.message.strip(),
                is_internal=False,
            )
        )

        self.session.add(ticket)
        await self.session.commit()
        return await self.get_ticket(ticket.id)

    async def list_user_tickets(self, actor: User) -> list[SupportTicket]:
        result = await self.session.scalars(
            select(SupportTicket)
            .where(SupportTicket.author_id == actor.id)
            .options(selectinload(SupportTicket.messages))
            .order_by(SupportTicket.created_at.desc())
        )
        return list(result.all())

    async def get_ticket(self, ticket_id) -> SupportTicket:
        ticket = await self.session.scalar(
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .options(selectinload(SupportTicket.messages))
        )
        if ticket is None:
            raise NotFoundError("Support ticket was not found.")
        return ticket
