import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_authenticated_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User, UserRole
from app.repositories import chunk_repository, document_repository
from app.schemas.knowledge import KnowledgeDocumentDetail, KnowledgeDocumentPublic
from app.services import document_parser, document_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
admin_router = APIRouter(prefix="/api/admin/knowledge", tags=["knowledge-admin"])


def _to_detail(
    document: KnowledgeDocument, *, chunk_count: int, include_error: bool
) -> KnowledgeDocumentDetail:
    data = KnowledgeDocumentPublic.model_validate(document).model_dump()
    return KnowledgeDocumentDetail(
        **data,
        chunk_count=chunk_count,
        error_message=document.error_message if include_error else None,
    )


@router.get("", response_model=list[KnowledgeDocumentPublic])
def list_knowledge_documents(
    category: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> list[KnowledgeDocument]:
    """Employees only ever see READY documents; admins see every status so
    they can monitor in-flight and failed uploads from the same list."""
    return document_service.list_visible_documents(
        db, is_admin=(user.role == UserRole.ADMIN), category=category, search=search
    )


@router.get("/{document_id}", response_model=KnowledgeDocumentDetail)
def get_knowledge_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
) -> KnowledgeDocumentDetail:
    is_admin = user.role == UserRole.ADMIN
    document = document_service.get_visible_document(db, document_id, is_admin=is_admin)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunk_count = chunk_repository.count_for_document(db, document.id)
    return _to_detail(document, chunk_count=chunk_count, include_error=is_admin)


@admin_router.post(
    "/upload", response_model=KnowledgeDocumentDetail, status_code=status.HTTP_202_ACCEPTED
)
def upload_knowledge_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> KnowledgeDocumentDetail:
    title = title.strip()
    category = category.strip()
    if not title or not category:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="title and category must not be empty.",
        )

    settings = get_settings()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    # Read at most one byte past the limit so an oversized upload doesn't have
    # to be fully buffered in memory before being rejected.
    file_bytes = file.file.read(max_size_bytes + 1)
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_size_mb} MB limit.",
        )

    try:
        document = document_service.create_document(
            db,
            title=title,
            original_filename=file.filename or "upload",
            description=description,
            category=category,
            uploaded_by=admin.id,
            file_bytes=file_bytes,
        )
    except document_parser.UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except document_parser.FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc

    background_tasks.add_task(document_service.process_document, document.id)
    return _to_detail(document, chunk_count=0, include_error=True)


@admin_router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document_service.delete_document(db, document)


@admin_router.post(
    "/{document_id}/reindex",
    response_model=KnowledgeDocumentDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
def reindex_knowledge_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> KnowledgeDocumentDetail:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document = document_service.start_reindex(db, document)
    background_tasks.add_task(document_service.process_document, document.id)
    chunk_count = chunk_repository.count_for_document(db, document.id)
    return _to_detail(document, chunk_count=chunk_count, include_error=True)
