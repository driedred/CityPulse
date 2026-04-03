from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.admin_reply import AdminReply
    from app.models.attachment import Attachment
    from app.models.issue import Issue
    from app.models.issue_vote import IssueVote
    from app.models.swipe_feedback import SwipeFeedback
    from app.models.ticket import Ticket


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.CITIZEN,
        nullable=False,
    )
    preferred_locale: Mapped[str] = mapped_column(String(12), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    issues: Mapped[list["Issue"]] = relationship(back_populates="author")
    issue_votes: Mapped[list["IssueVote"]] = relationship(back_populates="user")
    swipe_feedback: Mapped[list["SwipeFeedback"]] = relationship(back_populates="user")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="uploader")
    tickets_assigned: Mapped[list["Ticket"]] = relationship(back_populates="assigned_admin")
    admin_replies: Mapped[list["AdminReply"]] = relationship(back_populates="admin")
