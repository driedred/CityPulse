from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.support_ticket import SupportTicket
    from app.models.user import User


class TicketMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_messages"
    __table_args__ = (
        Index("ix_ticket_messages_ticket_created_at", "ticket_id", "created_at"),
    )

    ticket_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("support_tickets.id"),
        nullable=False,
    )
    author_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")
    author: Mapped[User] = relationship(back_populates="ticket_messages")
