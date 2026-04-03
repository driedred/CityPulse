import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def refresh_issue_recommendations(viewer_id: UUID) -> None:
    logger.info(
        "Recommendation refresh placeholder invoked for viewer_id=%s",
        viewer_id,
    )
