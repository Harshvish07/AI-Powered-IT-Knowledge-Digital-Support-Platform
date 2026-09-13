import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket_comment import TicketComment


def list_for_ticket(db: Session, ticket_id: uuid.UUID) -> list[TicketComment]:
    stmt = (
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
    )
    return list(db.scalars(stmt))


def create(db: Session, *, ticket_id: uuid.UUID, user_id: uuid.UUID, content: str) -> TicketComment:
    comment = TicketComment(ticket_id=ticket_id, user_id=user_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
