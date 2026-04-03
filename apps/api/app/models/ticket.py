from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TicketStatus

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.issue import Issue
    from app.models.user import User


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tickets"

    issue_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issues.id"),
        nullable=False,
    )
    assigned_admin_id: Mapped["UUID | None"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"),
        default=TicketStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    issue: Mapped["Issue"] = relationship(back_populates="tickets")
    assigned_admin: Mapped["User | None"] = relationship(back_populates="tickets_assigned")
