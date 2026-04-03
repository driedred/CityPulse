from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("", response_model=HealthResponse, summary="Service health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment,
        version=settings.app_version,
    )
