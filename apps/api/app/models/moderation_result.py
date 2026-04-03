from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ModerationStatus

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.issue import Issue


class ModerationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_results"

    issue_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issues.id"),
        nullable=False,
    )
    status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus, name="moderation_status"),
        default=ModerationStatus.PENDING,
        nullable=False,
    )
    provider_name: Mapped[str | None] = mapped_column(String(120))
    model_name: Mapped[str | None] = mapped_column(String(120))
    flags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)

    issue: Mapped["Issue"] = relationship(back_populates="moderation_results")
