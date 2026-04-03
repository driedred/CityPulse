from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Enum, Float, ForeignKey, Index, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AbuseRiskLevel

if TYPE_CHECKING:
    from app.models.user import User


class UserIntegritySnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_integrity_snapshots"
    __table_args__ = (
        Index("ix_user_integrity_snapshots_trust_score", "trust_score"),
        Index("ix_user_integrity_snapshots_abuse_risk_level", "abuse_risk_level"),
        Index("ix_user_integrity_snapshots_updated_at", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=55.0)
    trust_weight_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    abuse_risk_level: Mapped[AbuseRiskLevel] = mapped_column(
        Enum(AbuseRiskLevel, name="abuse_risk_level", native_enum=False),
        default=AbuseRiskLevel.LOW,
        nullable=False,
    )
    abuse_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sanction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trust_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    abuse_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped[User] = relationship(back_populates="integrity_snapshot")
