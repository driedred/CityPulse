from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(slots=True)
class TokenPayload:
    subject: UUID
    role: str
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def create_access_token(subject: UUID, role: str) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token.") from exc

    subject = payload.get("sub")
    role = payload.get("role")
    expires_at = payload.get("exp")

    if not subject or not role or not expires_at:
        raise AuthenticationError("Access token payload is incomplete.")

    return TokenPayload(
        subject=UUID(subject),
        role=str(role),
        expires_at=datetime.fromtimestamp(int(expires_at), tz=UTC),
    )
