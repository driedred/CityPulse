from enum import StrEnum


class UserRole(StrEnum):
    CITIZEN = "citizen"
    ADMIN = "admin"


class IssueStatus(StrEnum):
    DRAFT = "draft"
    PENDING_MODERATION = "pending_moderation"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ModerationState(StrEnum):
    NOT_REQUESTED = "not_requested"
    QUEUED = "queued"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"


class SwipeDirection(StrEnum):
    SUPPORT = "support"
    SKIP = "skip"
    MORE_LIKE_THIS = "more_like_this"
    LESS_LIKE_THIS = "less_like_this"


class DuplicateResolutionStatus(StrEnum):
    POSSIBLE = "possible"
    CONFIRMED = "confirmed"
    SUPPORTED_EXISTING = "supported_existing"
    DISMISSED = "dismissed"


class ModerationResultStatus(StrEnum):
    QUEUED = "queued"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ModerationLayer(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class AbuseRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntegrityEventSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SupportTicketType(StrEnum):
    APPEAL = "appeal"
    BUG_REPORT = "bug_report"
    IMPROVEMENT = "improvement"


class SupportTicketStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"
