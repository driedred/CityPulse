from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SupportTicketStatus, SupportTicketType

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.ticket_message import TicketMessage
    from app.models.user import User


class SupportTicket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("ix_support_tickets_author_created_at", "author_id", "created_at"),
        Index("ix_support_tickets_status_created_at", "status", "created_at"),
    )

    issue_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        nullable=True,
    )
    author_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    ticket_type: Mapped[SupportTicketType] = mapped_column(
        Enum(SupportTicketType, name="support_ticket_type", native_enum=False),
        nullable=False,
    )
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, name="support_ticket_status", native_enum=False),
        default=SupportTicketStatus.OPEN,
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(160), nullable=False)

    issue: Mapped[Issue | None] = relationship(back_populates="support_tickets")
    author: Mapped[User] = relationship(back_populates="support_tickets")
    messages: Mapped[list[TicketMessage]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at",
    )
