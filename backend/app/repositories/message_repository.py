import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message, MessageRole


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
