from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.models import User
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("A bearer token is required.")

    token_payload = decode_access_token(credentials.credentials)
    user = await session.scalar(select(User).where(User.id == token_payload.subject))

    if user is None or not user.is_active:
        raise AuthenticationError("The authenticated user could not be resolved.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_current_user(
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> User | None:
    if credentials is None:
        return None

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError("A bearer token is required.")

    token_payload = decode_access_token(credentials.credentials)
    user = await session.scalar(select(User).where(User.id == token_payload.subject))
    if user is None or not user.is_active:
        raise AuthenticationError("The authenticated user could not be resolved.")
    return user


CurrentOptionalUser = Annotated[User | None, Depends(get_optional_current_user)]


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], User]:
    async def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise AuthorizationError()
        return current_user

    return dependency
