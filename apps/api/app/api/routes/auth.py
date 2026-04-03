from fastapi import APIRouter, status

from app.api.deps import SessionDep
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep) -> UserRead:
    service = AuthService(session)
    user = await service.register_user(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    service = AuthService(session)
    user = await service.authenticate_user(payload)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user=UserRead.model_validate(user),
    )
