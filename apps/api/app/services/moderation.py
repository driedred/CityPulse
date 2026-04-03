from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from app.models.enums import ModerationStatus


@dataclass(slots=True)
class ModerationRequest:
    issue_id: UUID
    text: str
    media_keys: list[str] = field(default_factory=list)
    locale: str = "en"


@dataclass(slots=True)
class ModerationDecision:
    status: ModerationStatus
    confidence: float | None = None
    summary: str | None = None
    flags: dict[str, Any] = field(default_factory=dict)


class ModerationService(Protocol):
    async def moderate(self, payload: ModerationRequest) -> ModerationDecision:
        ...
