from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.tasks.moderation import enqueue_issue_moderation


class ModerationDispatcher(Protocol):
    async def enqueue_issue(self, issue_id: UUID) -> None:
        ...


class LogOnlyModerationDispatcher:
    async def enqueue_issue(self, issue_id: UUID) -> None:
        await enqueue_issue_moderation(issue_id)
