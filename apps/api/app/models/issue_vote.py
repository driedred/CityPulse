from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.issue import Issue
    from app.models.user import User


class IssueVote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_votes"
    __table_args__ = (
        UniqueConstraint("user_id", "issue_id", name="uq_issue_votes_user_issue"),
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
    value: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    user: Mapped["User"] = relationship(back_populates="issue_votes")
    issue: Mapped["Issue"] = relationship(back_populates="votes")
