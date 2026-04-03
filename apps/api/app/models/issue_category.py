from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.issue import Issue


class IssueCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issue_categories"
    __table_args__ = (
        Index("ix_issue_categories_slug_is_active", "slug", "is_active"),
    )

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    issues: Mapped[list[Issue]] = relationship(back_populates="category")
