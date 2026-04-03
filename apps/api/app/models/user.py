from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.admin_action_log import AdminActionLog
    from app.models.integrity_event import IntegrityEvent
    from app.models.issue import Issue
    from app.models.issue_attachment import IssueAttachment
    from app.models.issue_duplicate_link import IssueDuplicateLink
    from app.models.support_ticket import SupportTicket
    from app.models.swipe_feedback import SwipeFeedback
    from app.models.ticket_message import TicketMessage
    from app.models.user_integrity_snapshot import UserIntegritySnapshot


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role_is_active", "role", "is_active"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.CITIZEN,
        nullable=False,
    )
    preferred_locale: Mapped[str] = mapped_column(String(12), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issues: Mapped[list[Issue]] = relationship(back_populates="author")
    issue_attachments: Mapped[list[IssueAttachment]] = relationship(
        back_populates="uploader"
    )
    swipe_feedback_entries: Mapped[list[SwipeFeedback]] = relationship(
        back_populates="user"
    )
    support_tickets: Mapped[list[SupportTicket]] = relationship(
        back_populates="author"
    )
    ticket_messages: Mapped[list[TicketMessage]] = relationship(
        back_populates="author"
    )
    admin_action_logs: Mapped[list[AdminActionLog]] = relationship(
        back_populates="admin"
    )
    created_duplicate_links: Mapped[list[IssueDuplicateLink]] = relationship(
        back_populates="created_by_user"
    )
    integrity_snapshot: Mapped[UserIntegritySnapshot | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    integrity_events: Mapped[list[IntegrityEvent]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
