from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
