from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.issue import Issue


class IssueImpactSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_impact_snapshots"
    __table_args__ = (
        Index("ix_issue_impact_snapshots_public_score", "public_impact_score"),
        Index("ix_issue_impact_snapshots_updated_at", "updated_at"),
    )

    issue_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        unique=True,
        nullable=False,
    )
    public_impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    affected_people_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    score_version: Mapped[str] = mapped_column(String(32), default="impact-v1", nullable=False)
    signals: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    issue: Mapped[Issue] = relationship(back_populates="impact_snapshot")
