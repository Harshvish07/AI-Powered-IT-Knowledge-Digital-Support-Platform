import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.message import Message, MessageRole


def count_user_messages(db: Session) -> int:
    """Total number of questions ever asked of the assistant."""
    stmt = select(func.count()).select_from(Message).where(Message.role == MessageRole.USER)
    return db.scalar(stmt) or 0


def count_user_messages_by_day(db: Session, *, since: datetime) -> dict[date, int]:
    day = cast(Message.created_at, Date)
    stmt = (
        select(day, func.count())
        .where(Message.role == MessageRole.USER, Message.created_at >= since)
        .group_by(day)
    )
    return {message_day: count for message_day, count in db.execute(stmt)}


def count_by_conversation_ids(db: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    stmt = (
        select(Message.conversation_id, func.count())
        .where(Message.conversation_id.in_(ids))
        .group_by(Message.conversation_id)
    )
    return {conversation_id: count for conversation_id, count in db.execute(stmt)}


def list_for_conversation(db: Session, conversation_id: uuid.UUID) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.scalars(stmt))


def create(
    db: Session,
    *,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    confidence: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=sources,
        confidence=confidence,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
