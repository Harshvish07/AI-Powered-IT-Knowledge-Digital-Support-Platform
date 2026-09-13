import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.repositories import conversation_repository, message_repository, user_repository
from app.schemas.admin import AdminConversationSummary, DashboardMetrics
from app.services import dashboard_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> DashboardMetrics:
    return dashboard_service.get_dashboard_metrics(db)


def _to_conversation_summary(
    conversation: Conversation, *, message_count: int, users: dict[uuid.UUID, User]
) -> AdminConversationSummary:
    owner = users.get(conversation.user_id)
    return AdminConversationSummary(
        id=conversation.id,
        user_id=conversation.user_id,
        user_name=owner.full_name if owner else None,
        user_email=owner.email if owner else None,
        title=conversation.title,
        message_count=message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations", response_model=list[AdminConversationSummary])
def list_conversations(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
) -> list[AdminConversationSummary]:
    """Metadata only, for support/diagnostic purposes — message content is
    intentionally never returned here (see schemas.admin.AdminConversationSummary)."""
    conversations = conversation_repository.list_all(db)
    message_counts = message_repository.count_by_conversation_ids(db, {c.id for c in conversations})
    users = user_repository.get_by_ids(db, {c.user_id for c in conversations})
    users_by_id = {user.id: user for user in users}
    return [
        _to_conversation_summary(
            conversation, message_count=message_counts.get(conversation.id, 0), users=users_by_id
        )
        for conversation in conversations
    ]
