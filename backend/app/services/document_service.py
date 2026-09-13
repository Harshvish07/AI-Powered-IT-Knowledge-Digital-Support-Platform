"""Orchestrates the ingestion pipeline: validate -> store -> extract -> clean ->
chunk -> embed -> persist -> READY (or FAILED with a stored error message).

Kept HTTP-agnostic: the API layer only calls create_document/start_reindex/
delete_document/list_visible_documents/get_visible_document, and schedules
process_document as a background task. document_parser/chunking_service/
embedding_service errors are caught here and turned into a FAILED status
rather than leaking out of a background task.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.repositories import chunk_repository, document_repository
from app.services import chunking_service, document_parser, embedding_service

logger = logging.getLogger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 2000


class DocumentProcessingError(Exception):
    pass


def _storage_dir() -> Path:
    directory = Path(get_settings().upload_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _storage_path_for(document_id: uuid.UUID, extension: str) -> Path:
    return _storage_dir() / f"{document_id}{extension}"


def create_document(
    db: Session,
    *,
    title: str,
    original_filename: str,
    description: str | None,
    category: str,
    uploaded_by: uuid.UUID,
    file_bytes: bytes,
) -> KnowledgeDocument:
    """Validates and stores the uploaded file, then creates the DB record with
    status=UPLOADING. Does not run the pipeline — call process_document
    (typically scheduled as a FastAPI BackgroundTask) for that.
    """
    settings = get_settings()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    mime_type = document_parser.validate_upload(
        filename=original_filename,
        size_bytes=len(file_bytes),
        max_size_bytes=max_size_bytes,
    )
    if mime_type == "application/pdf" and not document_parser.looks_like_pdf(file_bytes[:5]):
        raise document_parser.UnsupportedFileTypeError(
            "File has a .pdf extension but its contents are not a valid PDF."
        )

    safe_filename = document_parser.sanitize_filename(original_filename)
    extension = Path(original_filename).suffix.lower()

    document_id = uuid.uuid4()
    storage_path = _storage_path_for(document_id, extension)
    storage_path.write_bytes(file_bytes)

    document = KnowledgeDocument(
        id=document_id,
        title=title,
        filename=safe_filename,
        description=description,
        category=category,
        uploaded_by=uploaded_by,
        status=DocumentStatus.UPLOADING,
        version=1,
        storage_path=str(storage_path),
        mime_type=mime_type,
        file_size_bytes=len(file_bytes),
    )
    return document_repository.add(db, document)


def process_document(document_id: uuid.UUID, db: Session | None = None) -> None:
    """The full extract->chunk->embed->persist pipeline for one document.

    Opens its own DB session by default — this normally runs after the
    request/response cycle (as a BackgroundTask) or standalone (from the
    demo-content seed script), so it can't reuse a request-scoped session.
    Tests pass `db` explicitly to run the pipeline inside the same
    transaction as the rest of the test (a separate connection wouldn't see
    not-yet-committed test data).
    """
    settings = get_settings()
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        document = document_repository.get_by_id(db, document_id)
        if document is None:
            logger.warning("process_document: document %s not found", document_id)
            return

        try:
            document_repository.update_status(db, document, status=DocumentStatus.PROCESSING)

            pages = document_parser.extract_text(Path(document.storage_path), document.mime_type)
            cleaned_pages = [
                document_parser.ExtractedPage(
                    page_number=page.page_number,
                    text=document_parser.clean_text(page.text),
                )
                for page in pages
            ]

            chunks = chunking_service.chunk_pages(
                cleaned_pages,
                chunk_size_tokens=settings.chunk_size_tokens,
                chunk_overlap_tokens=settings.chunk_overlap_tokens,
            )
            if not chunks:
                raise DocumentProcessingError(
                    "No extractable text content was found in this document."
                )

            document_repository.update_status(db, document, status=DocumentStatus.INDEXING)

            embeddings = embedding_service.generate_embeddings([chunk.content for chunk in chunks])

            chunk_rows = [
                {
                    "chunk_index": index,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "metadata": {"token_count": chunk.token_count},
                    "embedding": embedding,
                }
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ]
            chunk_repository.replace_for_document(db, document_id=document.id, chunks=chunk_rows)

            document_repository.update_status(db, document, status=DocumentStatus.READY)
        except Exception as exc:
            logger.exception("Document processing failed for %s", document_id)
            db.rollback()
            failed_document = document_repository.get_by_id(db, document_id)
            if failed_document is not None:
                document_repository.update_status(
                    db,
                    failed_document,
                    status=DocumentStatus.FAILED,
                    error_message=str(exc)[:MAX_ERROR_MESSAGE_LENGTH],
                )
    finally:
        if owns_session:
            db.close()


def start_reindex(db: Session, document: KnowledgeDocument) -> KnowledgeDocument:
    """Resets the document to UPLOADING and bumps its version; the caller is
    responsible for scheduling process_document(document.id) afterward."""
    return document_repository.bump_version_for_reindex(db, document)


def delete_document(db: Session, document: KnowledgeDocument) -> None:
    storage_path = Path(document.storage_path)
    document_repository.delete(db, document)  # cascades to document_chunks
    try:
        storage_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove stored file %s for a deleted document", storage_path)


def list_visible_documents(
    db: Session,
    *,
    is_admin: bool,
    category: str | None = None,
    search: str | None = None,
) -> list[KnowledgeDocument]:
    """Employees only ever see READY documents; admins see every status so
    they can monitor in-flight/failed uploads."""
    statuses = None if is_admin else [DocumentStatus.READY]
    return document_repository.list_documents(
        db, statuses=statuses, category=category, search=search
    )


def get_visible_document(
    db: Session, document_id: uuid.UUID, *, is_admin: bool
) -> KnowledgeDocument | None:
    document = document_repository.get_by_id(db, document_id)
    if document is None:
        return None
    if not is_admin and document.status != DocumentStatus.READY:
        return None
    return document
