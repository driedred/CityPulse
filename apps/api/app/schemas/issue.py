from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IssueStatus, ModerationState, SwipeDirection

DuplicateLookupStatus = Literal[
    "no_match",
    "possible_duplicates",
    "high_confidence_duplicate",
]
DuplicateRecommendedAction = Literal[
    "support_existing",
    "review_before_submit",
    "submit_new_issue",
]


class IssueCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    display_name: str
    description: str | None
    is_active: bool
    severity_baseline: float
    affected_people_baseline: int


class IssueAttachmentCreate(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0)
    storage_key: str = Field(min_length=3, max_length=255)


class IssueAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_id: UUID
    uploader_id: UUID
    storage_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime


class IssueCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    short_description: str = Field(min_length=10, max_length=4000)
    category_id: UUID
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    source_locale: str = Field(default="en", min_length=2, max_length=12)


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    title: str
    short_description: str
    latitude: float
    longitude: float
    status: IssueStatus
    moderation_state: ModerationState
    source_locale: str
    category: IssueCategoryRead
    attachments: list[IssueAttachmentRead]
    support_count: int = 0
    location_snippet: str = ""
    public_impact_score: float | None = None
    affected_people_estimate: int | None = None
    created_at: datetime
    updated_at: datetime


class PublicIssueSort(str):
    TOP = "top"
    RECENT = "recent"
    NEARBY = "nearby"


class IssuePublicImpactRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue_id: UUID
    public_impact_score: float
    affected_people_estimate: int
    importance_label: str
    score_version: str
    updated_at: datetime


class IssueImpactFactorRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    weight: float
    signal: float
    contribution: float
    raw_value: float | int | str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class IssueImpactAdminRead(IssuePublicImpactRead):
    signals: dict[str, Any] = Field(default_factory=dict)
    factors: list[IssueImpactFactorRead] = Field(default_factory=list)
    calculation_notes: list[str] = Field(default_factory=list)


class PublicIssueSummaryRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    short_description: str
    latitude: float
    longitude: float
    category: IssueCategoryRead
    location_snippet: str
    support_count: int
    public_impact_score: float | None = None
    affected_people_estimate: int | None = None
    importance_label: str | None = None
    cover_image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    distance_km: float | None = None


class PublicIssueDetailRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    short_description: str
    latitude: float
    longitude: float
    category: IssueCategoryRead
    location_snippet: str
    support_count: int
    public_impact_score: float | None = None
    affected_people_estimate: int | None = None
    importance_label: str | None = None
    cover_image_url: str | None = None
    source_locale: str
    attachments: list[IssueAttachmentRead]
    created_at: datetime
    updated_at: datetime


class PublicIssueMapMarkerRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    latitude: float
    longitude: float
    category: IssueCategoryRead
    location_snippet: str
    support_count: int
    public_impact_score: float | None = None
    affected_people_estimate: int | None = None
    importance_label: str | None = None


class IssueDuplicateSuggestionRequest(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    short_description: str = Field(min_length=10, max_length=4000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category_id: UUID | None = None
    image_hashes: list[str] = Field(default_factory=list, max_length=6)


class IssueDuplicateSuggestionRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue: PublicIssueSummaryRead
    existing_issue_id: UUID
    similarity_score: float
    reason_breakdown: list[str] = Field(default_factory=list)
    distance_km: float
    text_similarity: float
    category_match: bool
    recommended_action: DuplicateRecommendedAction
    image_similarity: float | None = None


class IssueDuplicateSuggestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DuplicateLookupStatus
    matches: list[IssueDuplicateSuggestionRead]


class IssueRewriteRequest(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    short_description: str = Field(min_length=10, max_length=4000)


class IssueRewriteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rewritten_title: str
    rewritten_description: str
    note: str


class IssueFeedbackCreate(BaseModel):
    action: SwipeDirection


class IssueFeedbackRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue_id: UUID
    action: SwipeDirection
    support_count: int
    support_changed: bool
    public_impact_score: float | None = None
    affected_people_estimate: int | None = None


class IssueSupportExistingRequest(BaseModel):
    candidate_title: str | None = Field(default=None, min_length=4, max_length=160)
    candidate_description: str | None = Field(
        default=None,
        min_length=10,
        max_length=4000,
    )
    candidate_category_id: UUID | None = None
    candidate_latitude: float | None = Field(default=None, ge=-90, le=90)
    candidate_longitude: float | None = Field(default=None, ge=-180, le=180)
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    distance_km: float | None = Field(default=None, ge=0)
    text_similarity: float | None = Field(default=None, ge=0, le=1)
    category_match: bool = False
    reason_breakdown: list[str] = Field(default_factory=list)
    image_hashes: list[str] = Field(default_factory=list, max_length=6)


class IssueSupportExistingRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_issue_id: UUID
    duplicate_link_id: UUID | None = None
    support_count: int
    support_changed: bool
    public_impact_score: float
    affected_people_estimate: int
