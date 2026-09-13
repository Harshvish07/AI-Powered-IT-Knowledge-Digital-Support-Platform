import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, field_validator, model_validator

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000
MAX_COMMENT_LENGTH = 2000


def _require_non_blank(value: str, *, field_name: str, max_length: int) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty.")
    if len(value) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters.")
    return value


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _require_non_blank(value, field_name="Title", max_length=MAX_TITLE_LENGTH)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        return _require_non_blank(
            value, field_name="Description", max_length=MAX_DESCRIPTION_LENGTH
        )


class TicketCommentCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _require_non_blank(value, field_name="Comment", max_length=MAX_COMMENT_LENGTH)


class TicketCommentPublic(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    user_id: uuid.UUID | None
    author_name: str | None
    content: str
    created_at: datetime


class TicketPublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    created_by: uuid.UUID
    created_by_name: str | None
    assigned_to: uuid.UUID | None
    assigned_to_name: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketPublic):
    comments: list[TicketCommentPublic]


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if self.status is None and self.priority is None:
            raise ValueError("Provide at least one of status or priority to update.")
        return self


class TicketAssign(BaseModel):
    assigned_to: uuid.UUID | None
