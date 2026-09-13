import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus


def get_by_id(db: Session, ticket_id: uuid.UUID) -> Ticket | None:
    return db.get(Ticket, ticket_id)


def count_all(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Ticket)) or 0


def count_by_status(db: Session) -> dict[TicketStatus, int]:
    counts = {status: 0 for status in TicketStatus}
    stmt = select(Ticket.status, func.count()).group_by(Ticket.status)
    for ticket_status, count in db.execute(stmt):
        counts[ticket_status] = count
    return counts


def count_by_category(db: Session) -> dict[TicketCategory, int]:
    counts = {category: 0 for category in TicketCategory}
    stmt = select(Ticket.category, func.count()).group_by(Ticket.category)
    for category, count in db.execute(stmt):
        counts[category] = count
    return counts


def list_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
) -> list[Ticket]:
    stmt = select(Ticket).where(Ticket.created_by == user_id)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if category is not None:
        stmt = stmt.where(Ticket.category == category)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    stmt = stmt.order_by(Ticket.created_at.desc())
    return list(db.scalars(stmt))


def list_all(
    db: Session,
    *,
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    assigned_to: uuid.UUID | None = None,
    search: str | None = None,
) -> list[Ticket]:
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if category is not None:
        stmt = stmt.where(Ticket.category == category)
    if priority is not None:
        stmt = stmt.where(Ticket.priority == priority)
    if assigned_to is not None:
        stmt = stmt.where(Ticket.assigned_to == assigned_to)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))
    stmt = stmt.order_by(Ticket.created_at.desc())
    return list(db.scalars(stmt))


def create(
    db: Session,
    *,
    title: str,
    description: str,
    category: TicketCategory,
    priority: TicketPriority,
    created_by: uuid.UUID,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description=description,
        category=category,
        priority=priority,
        status=TicketStatus.OPEN,
        created_by=created_by,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update(
    db: Session,
    ticket: Ticket,
    *,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
) -> Ticket:
    if status is not None:
        ticket.status = status
    if priority is not None:
        ticket.priority = priority
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def assign(db: Session, ticket: Ticket, *, assigned_to: uuid.UUID | None) -> Ticket:
    ticket.assigned_to = assigned_to
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket
