from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IssueCategory, IssueStatus

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.admin_reply import AdminReply
    from app.models.attachment import Attachment
    from app.models.issue_vote import IssueVote
    from app.models.moderation_result import ModerationResult
    from app.models.swipe_feedback import SwipeFeedback
    from app.models.ticket import Ticket
    from app.models.user import User


class Issue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("ix_issues_status_created_at", "status", "created_at"),
    )

    author_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[IssueCategory] = mapped_column(
        Enum(IssueCategory, name="issue_category"),
        default=IssueCategory.OTHER,
        nullable=False,
    )
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status"),
        default=IssueStatus.SUBMITTED,
        index=True,
        nullable=False,
    )
    source_locale: Mapped[str] = mapped_column(String(12), default="en", nullable=False)
    address_text: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    author: Mapped["User"] = relationship(back_populates="issues")
    votes: Mapped[list["IssueVote"]] = relationship(back_populates="issue")
    swipe_feedback: Mapped[list["SwipeFeedback"]] = relationship(back_populates="issue")
    moderation_results: Mapped[list["ModerationResult"]] = relationship(
        back_populates="issue"
    )
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="issue")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="issue")
    admin_replies: Mapped[list["AdminReply"]] = relationship(back_populates="issue")
