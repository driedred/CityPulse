from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IssueStatus, ModerationLayer, ModerationState

if TYPE_CHECKING:
    from app.models.issue_attachment import IssueAttachment
    from app.models.issue_category import IssueCategory
    from app.models.issue_duplicate_link import IssueDuplicateLink
    from app.models.issue_impact_snapshot import IssueImpactSnapshot
    from app.models.moderation_result import ModerationResult
    from app.models.support_ticket import SupportTicket
    from app.models.swipe_feedback import SwipeFeedback
    from app.models.user import User


class Issue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("ix_issues_author_created_at", "author_id", "created_at"),
        Index("ix_issues_status_created_at", "status", "created_at"),
        Index("ix_issues_category_created_at", "category_id", "created_at"),
    )

    author_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issue_categories.id"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status", native_enum=False),
        default=IssueStatus.PENDING_MODERATION,
        index=True,
        nullable=False,
    )
    moderation_state: Mapped[ModerationState] = mapped_column(
        Enum(ModerationState, name="moderation_state", native_enum=False),
        default=ModerationState.QUEUED,
        nullable=False,
    )
    source_locale: Mapped[str] = mapped_column(String(12), default="en", nullable=False)

    author: Mapped[User] = relationship(back_populates="issues")
    category: Mapped[IssueCategory] = relationship(back_populates="issues")
    swipe_feedback_entries: Mapped[list[SwipeFeedback]] = relationship(
        back_populates="issue"
    )
    moderation_results: Mapped[list[ModerationResult]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
    )
    impact_snapshot: Mapped[IssueImpactSnapshot | None] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        uselist=False,
    )
    attachments: Mapped[list[IssueAttachment]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
    )
    support_tickets: Mapped[list[SupportTicket]] = relationship(
        back_populates="issue"
    )
    canonical_duplicate_links: Mapped[list[IssueDuplicateLink]] = relationship(
        back_populates="canonical_issue",
        foreign_keys="IssueDuplicateLink.canonical_issue_id",
        cascade="all, delete-orphan",
    )
    duplicate_links: Mapped[list[IssueDuplicateLink]] = relationship(
        back_populates="duplicate_issue",
        foreign_keys="IssueDuplicateLink.duplicate_issue_id",
    )

    @property
    def latest_moderation_result(self) -> ModerationResult | None:
        if not self.moderation_results:
            return None
        return max(
            self.moderation_results,
            key=lambda item: (
                item.created_at,
                1 if item.layer == ModerationLayer.LLM else 0,
            ),
        )
