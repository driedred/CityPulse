import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def enqueue_issue_moderation(issue_id: UUID) -> None:
    logger.info("Issue moderation placeholder invoked for issue_id=%s", issue_id)
