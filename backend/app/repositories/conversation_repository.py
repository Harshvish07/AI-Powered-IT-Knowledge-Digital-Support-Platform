import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def get_by_id(db: Session, conversation_id: uuid.UUID) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def get_owned_by_id(
    db: Session, conversation_id: uuid.UUID, *, user_id: uuid.UUID
) -> Conversation | None:
    """Fetches a conversation only if it belongs to `user_id` — the caller
    can't tell an existing-but-not-theirs conversation apart from a
    genuinely nonexistent one, which is the point (no ownership probing)."""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        return None
    return conversation


def list_for_user(db: Session, user_id: uuid.UUID) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(db.scalars(stmt))


def create(db: Session, *, user_id: uuid.UUID, title: str) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def touch(db: Session, conversation: Conversation) -> None:
    """Bumps updated_at explicitly so the conversation list sorts
    most-recently-active first — a no-op flush wouldn't trigger the column's
    onupdate since nothing else on the row necessarily changed."""
    conversation.updated_at = datetime.now(UTC)
    db.add(conversation)
    db.commit()


def delete(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
    db.commit()
