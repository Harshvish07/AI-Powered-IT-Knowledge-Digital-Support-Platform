import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.message import MessageRole

MAX_MESSAGE_LENGTH = 4000

Confidence = Literal["high", "medium", "low", "none"]


class SourceCitation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    document_title: str
    chunk_id: uuid.UUID
    page: int | None
    relevance_score: float


class ChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty.")
        if len(value) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message must be at most {MAX_MESSAGE_LENGTH} characters.")
        return value


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    conversation_id: uuid.UUID
    confidence: Confidence


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    sources: list[SourceCitation] | None
    confidence: str | None
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut]
