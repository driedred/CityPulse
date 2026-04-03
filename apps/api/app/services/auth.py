from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import hash_password, verify_password
from app.models import User
from app.models.enums import UserRole
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_user(self, payload: RegisterRequest) -> User:
        normalized_email = payload.email.lower()
        existing_user = await self.session.scalar(
            select(User).where(User.email == normalized_email)
        )

        if existing_user is not None:
            raise ConflictError("A user with this email already exists.")

        user = User(
            email=normalized_email,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            preferred_locale=payload.preferred_locale,
            role=UserRole.CITIZEN,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, payload: LoginRequest) -> User:
        normalized_email = payload.email.lower()
        user = await self.session.scalar(select(User).where(User.email == normalized_email))

        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("This account is disabled.")

        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(user)
        return user
