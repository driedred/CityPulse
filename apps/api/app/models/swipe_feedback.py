from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SwipeDirection

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class SwipeFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "swipe_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "issue_id", name="uq_swipe_feedback_user_issue"),
        Index("ix_swipe_feedback_issue_created_at", "issue_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    issue_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        nullable=False,
    )
    direction: Mapped[SwipeDirection] = mapped_column(
        Enum(SwipeDirection, name="swipe_direction", native_enum=False),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="swipe_feedback_entries")
    issue: Mapped[Issue] = relationship(back_populates="swipe_feedback_entries")
