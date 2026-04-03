from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class IssueAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_attachments"
    __table_args__ = (
        Index("ix_issue_attachments_issue_created_at", "issue_id", "created_at"),
    )

    issue_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.id"),
        nullable=False,
    )
    uploader_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderation_image_url: Mapped[str | None] = mapped_column(Text)

    issue: Mapped[Issue] = relationship(back_populates="attachments")
    uploader: Mapped[User] = relationship(back_populates="issue_attachments")
