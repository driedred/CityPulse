from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IntegrityEventSeverity

if TYPE_CHECKING:
    from app.models.user import User


class IntegrityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integrity_events"
    __table_args__ = (
        Index("ix_integrity_events_user_created_at", "user_id", "created_at"),
        Index("ix_integrity_events_type_created_at", "event_type", "created_at"),
        Index("ix_integrity_events_severity_created_at", "severity", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[IntegrityEventSeverity] = mapped_column(
        Enum(IntegrityEventSeverity, name="integrity_event_severity", native_enum=False),
        default=IntegrityEventSeverity.LOW,
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(128))
    device_fingerprint_hash: Mapped[str | None] = mapped_column(String(128))

    user: Mapped[User] = relationship(back_populates="integrity_events")
