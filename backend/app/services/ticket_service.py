"""Ownership/role visibility rule for tickets: an employee may only reach a
ticket they created; an admin may reach any ticket. Kept in one place so the
"owner or admin" check isn't duplicated across the ticket-detail and
add-comment endpoints — mirrors document_service.get_visible_document from
the knowledge base module (Phase 3).
"""

import uuid

from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.repositories import ticket_repository


def get_visible_ticket(
    db: Session, ticket_id: uuid.UUID, *, user_id: uuid.UUID, is_admin: bool
) -> Ticket | None:
    ticket = ticket_repository.get_by_id(db, ticket_id)
    if ticket is None:
        return None
    if not is_admin and ticket.created_by != user_id:
        return None
    return ticket
