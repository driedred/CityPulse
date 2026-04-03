from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import AbuseRiskLevel, IntegrityEventSeverity, UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    preferred_locale: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserIdentityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    preferred_locale: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class IntegrityFactorRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    effect: Literal["positive", "negative", "risk"]
    signal: float | None = None
    points: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class IntegrityEventRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    event_type: str
    severity: IntegrityEventSeverity
    entity_type: str | None = None
    entity_id: UUID | None = None
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class UserIntegrityCompactRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: AdminUserIdentityRead
    trust_score: float
    trust_weight_multiplier: float
    abuse_risk_level: AbuseRiskLevel
    abuse_risk_score: float
    sanction_count: int = 0
    summary: str | None = None
    updated_at: datetime


class UserIntegritySummaryRead(UserIntegrityCompactRead):
    trust_factors: list[IntegrityFactorRead] = Field(default_factory=list)
    abuse_factors: list[IntegrityFactorRead] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class UserIntegrityDetailRead(UserIntegritySummaryRead):
    recent_events: list[IntegrityEventRead] = Field(default_factory=list)
