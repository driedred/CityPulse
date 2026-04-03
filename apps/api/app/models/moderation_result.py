from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ModerationLayer, ModerationResultStatus

if TYPE_CHECKING:
    from app.models.issue import Issue


class ModerationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_results"
    __table_args__ = (
        Index("ix_moderation_results_issue_created_at", "issue_id", "created_at"),
        Index("ix_moderation_results_status_created_at", "status", "created_at"),
        Index("ix_moderation_results_layer_status_created_at", "layer", "status", "created_at"),
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
    layer: Mapped[ModerationLayer] = mapped_column(
        Enum(ModerationLayer, name="moderation_layer", native_enum=False),
        default=ModerationLayer.DETERMINISTIC,
        nullable=False,
    )
    decision_code: Mapped[str] = mapped_column(String(48), default="queued", nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(120))
    model_name: Mapped[str | None] = mapped_column(String(120))
    machine_reasons: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    user_safe_explanation: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    escalation_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    normalized_category_slug: Mapped[str | None] = mapped_column(String(80))
    flags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)

    issue: Mapped[Issue] = relationship(back_populates="moderation_results")
