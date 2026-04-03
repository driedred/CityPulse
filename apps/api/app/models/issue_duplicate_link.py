from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DuplicateResolutionStatus

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class IssueDuplicateLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_duplicate_links"
    __table_args__ = (
        UniqueConstraint(
            "canonical_issue_id",
            "duplicate_issue_id",
            name="uq_issue_duplicate_links_canonical_duplicate",
        ),
        Index(
            "ix_issue_duplicate_links_canonical_status",
            "canonical_issue_id",
            "status",
        ),
        Index(
            "ix_issue_duplicate_links_duplicate_status",
            "duplicate_issue_id",
            "status",
        ),
    )

    canonical_issue_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        nullable=False,
    )
    duplicate_issue_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
    )
    status: Mapped[DuplicateResolutionStatus] = mapped_column(
        Enum(
            DuplicateResolutionStatus,
            name="duplicate_resolution_status",
            native_enum=False,
        ),
        default=DuplicateResolutionStatus.POSSIBLE,
        nullable=False,
    )
    similarity_score: Mapped[float | None] = mapped_column(Float)
    distance_km: Mapped[float | None] = mapped_column(Float)
    text_similarity: Mapped[float | None] = mapped_column(Float)
    category_match: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    candidate_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    canonical_issue: Mapped[Issue] = relationship(
        back_populates="canonical_duplicate_links",
        foreign_keys=[canonical_issue_id],
    )
    duplicate_issue: Mapped[Issue | None] = relationship(
        back_populates="duplicate_links",
        foreign_keys=[duplicate_issue_id],
    )
    created_by_user: Mapped[User | None] = relationship(
        back_populates="created_duplicate_links"
    )
