from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(slots=True)
class RecommendationContext:
    viewer_id: UUID
    locale: str = "en"
    city: str | None = None
    excluded_issue_ids: list[UUID] = field(default_factory=list)


class RecommendationService(Protocol):
    async def rank_issue_feed(self, context: RecommendationContext) -> list[UUID]:
        ...
