import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.knowledge_document import DocumentStatus


class KnowledgeDocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    description: str | None
    category: str
    status: DocumentStatus
    version: int
    file_size_bytes: int
    uploaded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentDetail(KnowledgeDocumentPublic):
    chunk_count: int
    # Server-side detail, only ever populated in the response for ADMIN callers.
    error_message: str | None = None
