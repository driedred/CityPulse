from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SwipeDirection

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.issue import Issue
    from app.models.user import User


class SwipeFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "swipe_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "issue_id", name="uq_swipe_feedback_user_issue"),
    )

    user_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    issue_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issues.id"),
        nullable=False,
    )
    direction: Mapped[SwipeDirection] = mapped_column(
        Enum(SwipeDirection, name="swipe_direction"),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="swipe_feedback")
    issue: Mapped["Issue"] = relationship(back_populates="swipe_feedback")
