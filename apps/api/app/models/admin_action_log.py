from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AdminActionLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_action_logs"
    __table_args__ = (
        Index("ix_admin_action_logs_admin_created_at", "admin_id", "created_at"),
        Index(
            "ix_admin_action_logs_entity_type_entity_id",
            "entity_type",
            "entity_id",
        ),
    )

    admin_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    note: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    admin: Mapped[User] = relationship(back_populates="admin_action_logs")
