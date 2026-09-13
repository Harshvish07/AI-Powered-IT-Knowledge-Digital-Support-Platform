"""Aggregates real database counts for the admin dashboard (Phase 6). Every
number here comes from an actual query against the current data — nothing is
hardcoded — so the dashboard reflects the live state of the platform.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.knowledge_document import DocumentStatus
from app.models.ticket import TicketStatus
from app.repositories import (
    document_repository,
    message_repository,
    ticket_repository,
    user_repository,
)
from app.schemas.admin import DailyCount, DashboardMetrics

AI_QUESTIONS_HISTORY_DAYS = 14


def _ai_questions_by_day(db: Session) -> list[DailyCount]:
    since = datetime.now(UTC) - timedelta(days=AI_QUESTIONS_HISTORY_DAYS - 1)
    counts_by_day = message_repository.count_user_messages_by_day(db, since=since)

    days: list[DailyCount] = []
    for offset in range(AI_QUESTIONS_HISTORY_DAYS):
        day = (since + timedelta(days=offset)).date()
        days.append(DailyCount(date=day, count=counts_by_day.get(day, 0)))
    return days


def get_dashboard_metrics(db: Session) -> DashboardMetrics:
    documents_by_status = document_repository.count_by_status(db)
    tickets_by_status = ticket_repository.count_by_status(db)

    return DashboardMetrics(
        total_users=user_repository.count_all(db),
        active_users=user_repository.count_active(db),
        total_documents=document_repository.count_all(db),
        ready_documents=documents_by_status[DocumentStatus.READY],
        failed_documents=documents_by_status[DocumentStatus.FAILED],
        total_tickets=ticket_repository.count_all(db),
        open_tickets=tickets_by_status[TicketStatus.OPEN],
        in_progress_tickets=tickets_by_status[TicketStatus.IN_PROGRESS],
        resolved_tickets=tickets_by_status[TicketStatus.RESOLVED],
        ai_questions=message_repository.count_user_messages(db),
        tickets_by_status=tickets_by_status,
        tickets_by_category=ticket_repository.count_by_category(db),
        documents_by_status=documents_by_status,
        ai_questions_by_day=_ai_questions_by_day(db),
    )
