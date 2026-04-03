from fastapi import APIRouter

from app.api.routes import admin, health, issues
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(health.router)
api_router.include_router(issues.router)
api_router.include_router(admin.router)
