from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.models.enums import IssueCategory


@dataclass(slots=True)
class IssueSubmissionPayload:
    reporter_id: UUID | None
    title: str
    description: str
    category: IssueCategory
    source_locale: str
    address_text: str | None = None
    city: str | None = None
    attachment_keys: list[str] = field(default_factory=list)


class IssueWorkflowService(Protocol):
    async def submit_issue(self, payload: IssueSubmissionPayload) -> UUID:
        ...
