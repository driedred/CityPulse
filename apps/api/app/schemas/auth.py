from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    preferred_locale: str = Field(default="en", min_length=2, max_length=12)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"
    user: UserRead
