import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_authenticated_user
from app.core.database import get_db
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.ticket_comment import TicketComment
from app.models.user import User, UserRole
from app.repositories import ticket_comment_repository, ticket_repository, user_repository
from app.schemas.ticket import (
    TicketAssign,
    TicketCommentCreate,
    TicketCommentPublic,
    TicketCreate,
    TicketDetail,
    TicketPublic,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
admin_router = APIRouter(prefix="/api/admin/tickets", tags=["tickets-admin"])


def _user_map(
    db: Session, tickets: list[Ticket], comments: list[TicketComment] | None = None
) -> dict[uuid.UUID, User]:
    ids: set[uuid.UUID] = set()
    for ticket in tickets:
        ids.add(ticket.created_by)
        if ticket.assigned_to is not None:
            ids.add(ticket.assigned_to)
    for comment in comments or []:
        if comment.user_id is not None:
            ids.add(comment.user_id)
    return {user.id: user for user in user_repository.get_by_ids(db, ids)}


def _to_ticket_public(ticket: Ticket, users: dict[uuid.UUID, User]) -> TicketPublic:
    created_by_user = users.get(ticket.created_by)
    assigned_to_user = users.get(ticket.assigned_to) if ticket.assigned_to is not None else None
    return TicketPublic(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        created_by=ticket.created_by,
        created_by_name=created_by_user.full_name if created_by_user else None,
        assigned_to=ticket.assigned_to,
        assigned_to_name=assigned_to_user.full_name if assigned_to_user else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def _to_comment_public(comment: TicketComment, users: dict[uuid.UUID, User]) -> TicketCommentPublic:
    author = users.get(comment.user_id) if comment.user_id is not None else None
    return TicketCommentPublic(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        author_name=author.full_name if author else None,
        content=comment.content,
        created_at=comment.created_at,
    )


def _to_ticket_detail(
    ticket: Ticket, comments: list[TicketComment], users: dict[uuid.UUID, User]
) -> TicketDetail:
    return TicketDetail(
        **_to_ticket_public(ticket, users).model_dump(),
        comments=[_to_comment_public(comment, users) for comment in comments],
    )


def _load_detail(db: Session, ticket: Ticket) -> TicketDetail:
    comments = ticket_comment_repository.list_for_ticket(db, ticket.id)
    users = _user_map(db, [ticket], comments)
    return _to_ticket_detail(ticket, comments, users)


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> TicketDetail:
    ticket = ticket_repository.create(
        db,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        created_by=user.id,
    )
    return _load_detail(db, ticket)


@router.get("", response_model=list[TicketPublic])
def list_my_tickets(
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> list[TicketPublic]:
    tickets = ticket_repository.list_for_user(
        db, user.id, status=status, category=category, priority=priority
    )
    users = _user_map(db, tickets)
    return [_to_ticket_public(ticket, users) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> TicketDetail:
    ticket = ticket_service.get_visible_ticket(
        db, ticket_id, user_id=user.id, is_admin=(user.role == UserRole.ADMIN)
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return _load_detail(db, ticket)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentPublic,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(
    ticket_id: uuid.UUID,
    payload: TicketCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> TicketCommentPublic:
    ticket = ticket_service.get_visible_ticket(
        db, ticket_id, user_id=user.id, is_admin=(user.role == UserRole.ADMIN)
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    comment = ticket_comment_repository.create(
        db, ticket_id=ticket.id, user_id=user.id, content=payload.content
    )
    return _to_comment_public(comment, {user.id: user})


# ---- Admin ----


@admin_router.get("", response_model=list[TicketPublic])
def list_all_tickets(
    status: TicketStatus | None = None,
    category: TicketCategory | None = None,
    priority: TicketPriority | None = None,
    assigned_to: uuid.UUID | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[TicketPublic]:
    tickets = ticket_repository.list_all(
        db,
        status=status,
        category=category,
        priority=priority,
        assigned_to=assigned_to,
        search=search,
    )
    users = _user_map(db, tickets)
    return [_to_ticket_public(ticket, users) for ticket in tickets]


@admin_router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TicketDetail:
    ticket = ticket_repository.get_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    ticket = ticket_repository.update(db, ticket, status=payload.status, priority=payload.priority)
    return _load_detail(db, ticket)


@admin_router.post("/{ticket_id}/assign", response_model=TicketDetail)
def assign_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAssign,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TicketDetail:
    ticket = ticket_repository.get_by_id(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if payload.assigned_to is not None:
        assignee = user_repository.get_by_id(db, payload.assigned_to)
        if assignee is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="assigned_to does not match an existing user.",
            )
    ticket = ticket_repository.assign(db, ticket, assigned_to=payload.assigned_to)
    return _load_detail(db, ticket)
