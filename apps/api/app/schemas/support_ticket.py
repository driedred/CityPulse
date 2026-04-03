from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SupportTicketStatus, SupportTicketType


class SupportTicketCreate(BaseModel):
    issue_id: UUID | None = None
    ticket_type: SupportTicketType = Field(
        validation_alias="type",
        serialization_alias="type",
    )
    subject: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=4, max_length=4000)

    model_config = ConfigDict(populate_by_name=True)


class TicketMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_id: UUID
    author_id: UUID
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    issue_id: UUID | None
    author_id: UUID
    ticket_type: SupportTicketType = Field(serialization_alias="type")
    status: SupportTicketStatus
    subject: str
    messages: list[TicketMessageRead]
    created_at: datetime
    updated_at: datetime
