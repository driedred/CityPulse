from enum import Enum


class UserRole(str, Enum):
    CITIZEN = "citizen"
    ADMIN = "admin"


class IssueCategory(str, Enum):
    ROADS = "roads"
    SANITATION = "sanitation"
    LIGHTING = "lighting"
    SAFETY = "safety"
    OTHER = "other"


class IssueStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class SwipeDirection(str, Enum):
    PRIORITIZE = "prioritize"
    SKIP = "skip"
    DEPRIORITIZE = "deprioritize"


class ModerationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"
