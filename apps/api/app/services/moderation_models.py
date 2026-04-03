from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ModerationAttachmentDescriptor:
    original_filename: str
    content_type: str
    size_bytes: int
    moderation_image_url: str | None = None


@dataclass(frozen=True, slots=True)
class ModerationSubmission:
    issue_id: UUID
    author_id: UUID
    title: str
    short_description: str
    category_slug: str
    source_locale: str
    latitude: float
    longitude: float
    attachments: tuple[ModerationAttachmentDescriptor, ...] = ()
