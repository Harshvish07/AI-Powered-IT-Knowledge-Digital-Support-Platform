import uuid
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk


def count_for_document(db: Session, document_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
    )
    return db.scalar(stmt) or 0


def delete_for_document(db: Session, document_id: uuid.UUID) -> None:
    db.execute(sa_delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.commit()


def bulk_create(
    db: Session,
    *,
    document_id: uuid.UUID,
    chunks: list[dict[str, Any]],
) -> list[DocumentChunk]:
    """`chunks` items: {chunk_index, content, page_number, metadata, embedding}."""
    rows = [
        DocumentChunk(
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            page_number=chunk.get("page_number"),
            chunk_metadata=chunk.get("metadata"),
            embedding=chunk["embedding"],
        )
        for chunk in chunks
    ]
    db.add_all(rows)
    db.commit()
    return rows


def replace_for_document(
    db: Session,
    *,
    document_id: uuid.UUID,
    chunks: list[dict[str, Any]],
) -> list[DocumentChunk]:
    delete_for_document(db, document_id)
    return bulk_create(db, document_id=document_id, chunks=chunks)
