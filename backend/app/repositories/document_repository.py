import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_document import DocumentStatus, KnowledgeDocument


def get_by_id(db: Session, document_id: uuid.UUID) -> KnowledgeDocument | None:
    return db.get(KnowledgeDocument, document_id)


def count_all(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(KnowledgeDocument)) or 0


def count_by_status(db: Session) -> dict[DocumentStatus, int]:
    counts = {status: 0 for status in DocumentStatus}
    stmt = select(KnowledgeDocument.status, func.count()).group_by(KnowledgeDocument.status)
    for doc_status, count in db.execute(stmt):
        counts[doc_status] = count
    return counts


def list_documents(
    db: Session,
    *,
    statuses: list[DocumentStatus] | None = None,
    category: str | None = None,
    search: str | None = None,
) -> list[KnowledgeDocument]:
    stmt = select(KnowledgeDocument)
    if statuses is not None:
        stmt = stmt.where(KnowledgeDocument.status.in_(statuses))
    if category:
        stmt = stmt.where(KnowledgeDocument.category == category)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                KnowledgeDocument.title.ilike(pattern),
                KnowledgeDocument.description.ilike(pattern),
                KnowledgeDocument.category.ilike(pattern),
            )
        )
    stmt = stmt.order_by(KnowledgeDocument.created_at.desc())
    return list(db.scalars(stmt))


def add(db: Session, document: KnowledgeDocument) -> KnowledgeDocument:
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_status(
    db: Session,
    document: KnowledgeDocument,
    *,
    status: DocumentStatus,
    error_message: str | None = None,
) -> KnowledgeDocument:
    document.status = status
    document.error_message = error_message
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def bump_version_for_reindex(db: Session, document: KnowledgeDocument) -> KnowledgeDocument:
    document.version += 1
    document.status = DocumentStatus.UPLOADING
    document.error_message = None
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete(db: Session, document: KnowledgeDocument) -> None:
    db.delete(document)
    db.commit()
