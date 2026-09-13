import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.knowledge_document import DocumentStatus
from app.models.ticket import TicketCategory, TicketStatus


class DailyCount(BaseModel):
    date: date
    count: int


class DashboardMetrics(BaseModel):
    total_users: int
    active_users: int
    total_documents: int
    ready_documents: int
    failed_documents: int
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    ai_questions: int

    tickets_by_status: dict[TicketStatus, int]
    tickets_by_category: dict[TicketCategory, int]
    documents_by_status: dict[DocumentStatus, int]
    ai_questions_by_day: list[DailyCount]


class AdminConversationSummary(BaseModel):
    """Metadata only — never message content — for support/diagnostic use."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None
    user_email: str | None
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
