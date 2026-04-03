from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Enum, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ModerationResultStatus

if TYPE_CHECKING:
    from app.models.issue import Issue


class ModerationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_results"
    __table_args__ = (
        Index("ix_moderation_results_issue_created_at", "issue_id", "created_at"),
        Index("ix_moderation_results_status_created_at", "status", "created_at"),
    )

    issue_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        nullable=False,
    )
    status: Mapped[ModerationResultStatus] = mapped_column(
        Enum(ModerationResultStatus, name="moderation_result_status", native_enum=False),
        default=ModerationResultStatus.QUEUED,
        nullable=False,
    )
    provider_name: Mapped[str | None] = mapped_column(String(120))
    model_name: Mapped[str | None] = mapped_column(String(120))
    flags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)

    issue: Mapped[Issue] = relationship(back_populates="moderation_results")
