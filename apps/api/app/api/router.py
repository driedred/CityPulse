from fastapi import APIRouter

from app.api.routes import auth, health, issues, tickets, users
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(issues.router)
api_router.include_router(tickets.router)
api_router.include_router(users.router)
