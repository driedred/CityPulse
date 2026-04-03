from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from uuid import UUID

    from app.models.issue import Issue
    from app.models.user import User


class AdminReply(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_replies"

    issue_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("issues.id"),
        nullable=False,
    )
    admin_id: Mapped["UUID"] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    issue: Mapped["Issue"] = relationship(back_populates="admin_replies")
    admin: Mapped["User"] = relationship(back_populates="admin_replies")
