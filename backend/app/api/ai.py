import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import require_authenticated_user
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.conversation import Conversation
from app.models.message import MessageRole
from app.models.user import User
from app.repositories import conversation_repository, message_repository
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    MessageOut,
    SourceCitation,
)
from app.services import embedding_service, llm_service, rag_service

router = APIRouter(prefix="/api/ai", tags=["ai"])

_SERVICE_UNAVAILABLE_MESSAGE = (
    "The AI assistant is temporarily unavailable. Please try again shortly."
)

MAX_TITLE_LENGTH = 60


def _title_from_message(message: str) -> str:
    stripped = message.strip()
    if len(stripped) <= MAX_TITLE_LENGTH:
        return stripped
    return stripped[: MAX_TITLE_LENGTH - 1].rstrip() + "…"


def _sources_payload(chunks: list[rag_service.RetrievedChunk]) -> list[dict[str, object]]:
    return [
        SourceCitation(
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            chunk_id=chunk.chunk_id,
            page=chunk.page_number,
            relevance_score=round(chunk.similarity, 4),
        ).model_dump(mode="json")
        for chunk in chunks
    ]


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> ChatResponse:
    if payload.conversation_id is not None:
        conversation = conversation_repository.get_owned_by_id(
            db, payload.conversation_id, user_id=user.id
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
    else:
        conversation = conversation_repository.create(
            db, user_id=user.id, title=_title_from_message(payload.message)
        )

    message_repository.create(
        db, conversation_id=conversation.id, role=MessageRole.USER, content=payload.message
    )

    try:
        result = rag_service.answer_question(db, payload.message)
    except (
        embedding_service.EmbeddingConfigurationError,
        embedding_service.EmbeddingGenerationError,
        llm_service.LLMConfigurationError,
        llm_service.LLMGenerationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_SERVICE_UNAVAILABLE_MESSAGE,
        ) from exc

    sources_payload = _sources_payload(result.sources)
    message_repository.create(
        db,
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result.answer,
        sources=sources_payload,
        confidence=result.confidence,
    )
    conversation_repository.touch(db, conversation)

    return ChatResponse(
        answer=result.answer,
        sources=[SourceCitation.model_validate(source) for source in sources_payload],
        conversation_id=conversation.id,
        confidence=result.confidence,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> list[Conversation]:
    return conversation_repository.list_for_user(db, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> ConversationDetail:
    conversation = conversation_repository.get_owned_by_id(db, conversation_id, user_id=user.id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = message_repository.list_for_conversation(db, conversation.id)
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageOut.model_validate(message) for message in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> None:
    conversation = conversation_repository.get_owned_by_id(db, conversation_id, user_id=user.id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conversation_repository.delete(db, conversation)
