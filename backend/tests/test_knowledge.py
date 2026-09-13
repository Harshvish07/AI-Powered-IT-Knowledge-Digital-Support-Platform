import io
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.document_chunk import DocumentChunk
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.services import chunking_service, document_parser, document_service, embedding_service
from tests.conftest import unique_email

settings = get_settings()
VALID_PASSWORD = "StrongPass1!"


# ---- Fixtures ----


@pytest.fixture(autouse=True)
def _isolated_storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Uploads during tests land in a throwaway directory, never backend/storage/."""
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path / "uploads"))


@pytest.fixture()
def fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces the real Gemini call with a deterministic fake vector generator —
    this is the unit-test boundary the brief asks for: mock the external API
    call, exercise every surrounding line of real pipeline code."""

    def _fake_generate(texts: list[str], *, client: object | None = None) -> list[list[float]]:
        return [
            [float((i + 1) % 7) / 7.0] * settings.embedding_dimensions for i in range(len(texts))
        ]

    monkeypatch.setattr(embedding_service, "generate_embeddings", _fake_generate)


def _create_user(db: Session, *, role: UserRole) -> User:
    return user_repository.create(
        db,
        email=unique_email("kb"),
        password_hash=hash_password(VALID_PASSWORD),
        full_name="Knowledge Base Test User",
        role=role,
    )


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    user = _create_user(db_session, role=UserRole.ADMIN)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}


def _employee_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    user = _create_user(db_session, role=UserRole.EMPLOYEE)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}


def _upload(
    client: TestClient,
    headers: dict[str, str],
    *,
    filename: str,
    content: bytes,
    content_type: str,
    title: str | None = None,
    category: str = "Networking",
    description: str = "A test document.",
):
    return client.post(
        "/api/admin/knowledge/upload",
        headers=headers,
        data={
            "title": title or f"Doc {uuid.uuid4().hex[:8]}",
            "category": category,
            "description": description,
        },
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def _sample_pdf_bytes() -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.drawString(100, 700, "VPN Setup Guide")
    pdf.drawString(100, 680, "This is a demo PDF used for automated testing purposes only.")
    pdf.showPage()
    pdf.drawString(100, 700, "Page two contains additional troubleshooting text for the guide.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


# ---- Upload: supported formats ----


def test_upload_valid_pdf_processes_to_ready(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="guide.pdf",
        content=_sample_pdf_bytes(),
        content_type="application/pdf",
    )
    assert response.status_code == 202
    document_id = response.json()["id"]
    assert response.json()["status"] == "UPLOADING"

    document_service.process_document(uuid.UUID(document_id), db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "READY"
    assert body["chunk_count"] >= 1

    chunks = db_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(document_id))
    ).all()
    assert any(c.page_number == 1 for c in chunks)


def test_upload_valid_txt_processes_to_ready(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    content = b"Password Reset Procedure\n\nThis explains how to reset your password safely."
    response = _upload(
        client, headers, filename="notes.txt", content=content, content_type="text/plain"
    )
    assert response.status_code == 202
    document_id = response.json()["id"]

    document_service.process_document(uuid.UUID(document_id), db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers)
    assert detail.json()["status"] == "READY"
    assert detail.json()["chunk_count"] >= 1


def test_upload_valid_markdown_processes_to_ready(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    content = b"# MFA Setup Guide\n\nFollow these steps to enable MFA.\n\nStep one."
    response = _upload(
        client, headers, filename="mfa.md", content=content, content_type="text/markdown"
    )
    assert response.status_code == 202
    document_id = response.json()["id"]

    document_service.process_document(uuid.UUID(document_id), db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers)
    assert detail.json()["status"] == "READY"


# ---- Upload: validation ----


def test_upload_unsupported_file_type_rejected(client: TestClient, db_session: Session) -> None:
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="app.exe",
        content=b"MZ\x90\x00fake-binary",
        content_type="application/octet-stream",
    )
    assert response.status_code == 415


def test_upload_oversized_file_rejected(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    headers = _admin_headers(client, db_session)
    oversized_content = b"x" * (2 * 1024 * 1024)
    response = _upload(
        client, headers, filename="big.txt", content=oversized_content, content_type="text/plain"
    )
    assert response.status_code == 413


# ---- Text extraction ----


def test_extract_text_txt(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("Hello knowledge base.\n\nSecond paragraph.", encoding="utf-8")

    pages = document_parser.extract_text(path, "text/plain")

    assert len(pages) == 1
    assert pages[0].page_number is None
    assert "Hello knowledge base." in pages[0].text


def test_extract_text_pdf_pages(tmp_path: Path) -> None:
    path = tmp_path / "sample.pdf"
    path.write_bytes(_sample_pdf_bytes())

    pages = document_parser.extract_text(path, "application/pdf")

    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert "VPN Setup Guide" in pages[0].text
    assert "troubleshooting" in pages[1].text


# ---- Chunking ----


def test_chunking_respects_size_and_preserves_paragraphs() -> None:
    paragraphs = [
        f"Paragraph number {i} with some extra filler words to add tokens." for i in range(20)
    ]
    text = "\n\n".join(paragraphs)
    pages = [document_parser.ExtractedPage(page_number=None, text=text)]

    chunks = chunking_service.chunk_pages(pages, chunk_size_tokens=50, chunk_overlap_tokens=10)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 50
        # Every paragraph inside a chunk should be a whole, unmodified paragraph.
        for part in chunk.content.split("\n\n"):
            assert part.strip() in paragraphs


def test_chunking_applies_overlap_between_consecutive_chunks() -> None:
    paragraphs = [
        f"Paragraph number {i} with some extra filler words to add tokens." for i in range(20)
    ]
    text = "\n\n".join(paragraphs)
    pages = [document_parser.ExtractedPage(page_number=None, text=text)]

    chunks = chunking_service.chunk_pages(pages, chunk_size_tokens=50, chunk_overlap_tokens=15)

    assert len(chunks) > 1
    first_chunk_paragraphs = set(chunks[0].content.split("\n\n"))
    second_chunk_paragraphs = set(chunks[1].content.split("\n\n"))
    assert (
        first_chunk_paragraphs & second_chunk_paragraphs
    ), "expected shared (overlapping) paragraphs"


def test_chunking_hard_splits_a_single_oversized_paragraph() -> None:
    huge_paragraph = " ".join(f"word{i}" for i in range(500))
    pages = [document_parser.ExtractedPage(page_number=3, text=huge_paragraph)]

    chunks = chunking_service.chunk_pages(pages, chunk_size_tokens=50, chunk_overlap_tokens=10)

    assert len(chunks) > 1
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert all(chunk.token_count <= 50 for chunk in chunks)


# ---- Metadata, embeddings, persistence ----


def test_chunk_metadata_and_embeddings_are_persisted(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    content = b"Wi-Fi Configuration Guide\n\nConnect to the office network using these steps."
    response = _upload(
        client, headers, filename="wifi.txt", content=content, content_type="text/plain"
    )
    document_id = uuid.UUID(response.json()["id"])

    document_service.process_document(document_id, db=db_session)

    chunks = db_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.chunk_metadata is not None
        assert "token_count" in chunk.chunk_metadata
        assert len(chunk.embedding) == settings.embedding_dimensions


def test_database_persistence_document_and_chunks_linked(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="policy.md",
        content=b"# Policy\n\nSome policy text.\n\nMore policy text here.",
        content_type="text/markdown",
    )
    document_id = uuid.UUID(response.json()["id"])
    document_service.process_document(document_id, db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    chunk_rows = db_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    assert detail["chunk_count"] == len(chunk_rows)
    assert all(c.document_id == document_id for c in chunk_rows)


# ---- Failure handling ----


def test_failed_embedding_marks_document_failed_with_error(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(texts: list[str], *, client: object | None = None) -> list[list[float]]:
        raise embedding_service.EmbeddingGenerationError("simulated embedding outage")

    monkeypatch.setattr(embedding_service, "generate_embeddings", _boom)

    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="broken.txt",
        content=b"Some content to embed.",
        content_type="text/plain",
    )
    document_id = uuid.UUID(response.json()["id"])

    document_service.process_document(document_id, db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    assert detail["status"] == "FAILED"
    assert detail["error_message"]


def test_upload_corrupted_pdf_rejected(client: TestClient, db_session: Session) -> None:
    """A .pdf extension with non-PDF bytes must be caught by the magic-byte
    sniff at upload time — before any storage or processing happens — not
    merely fail later during text extraction."""
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="fake.pdf",
        content=b"This is not really a PDF file, just renamed.",
        content_type="application/pdf",
    )
    assert response.status_code == 415
    assert "not a valid PDF" in response.json()["detail"]


def test_empty_document_marks_failed_with_clear_error(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    """A supported file type with no extractable text content (e.g. an empty
    .txt file) must fail cleanly at the chunking step, not crash or silently
    produce a READY document with zero chunks."""
    headers = _admin_headers(client, db_session)
    response = _upload(
        client, headers, filename="empty.txt", content=b"", content_type="text/plain"
    )
    document_id = uuid.UUID(response.json()["id"])

    document_service.process_document(document_id, db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    assert detail["status"] == "FAILED"
    assert "No extractable text" in detail["error_message"]


def test_large_document_chunks_and_indexes_successfully(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    """A document large enough to produce many chunks (rather than the usual
    single-digit chunk count in other tests) must still process end to end —
    a reliability check that chunking/embedding isn't implicitly assuming a
    small document."""
    headers = _admin_headers(client, db_session)
    # ~400 short paragraphs comfortably exceeds the default chunk size many
    # times over, forcing dozens of chunks without approaching the upload
    # size limit.
    paragraphs = [
        f"Paragraph {i}: this is filler text for a large knowledge base document "
        "used to verify that chunking and embedding scale past a handful of chunks."
        for i in range(400)
    ]
    content = "\n\n".join(paragraphs).encode("utf-8")

    response = _upload(
        client, headers, filename="large.txt", content=content, content_type="text/plain"
    )
    assert response.status_code == 202
    document_id = uuid.UUID(response.json()["id"])

    document_service.process_document(document_id, db=db_session)

    detail = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    assert detail["status"] == "READY"
    assert detail["chunk_count"] > 10


# ---- Authorization ----


def test_upload_requires_admin(client: TestClient, db_session: Session) -> None:
    employee_headers = _employee_headers(client, db_session)
    response = _upload(
        client, employee_headers, filename="notes.txt", content=b"hello", content_type="text/plain"
    )
    assert response.status_code == 403

    response_unauth = client.post(
        "/api/admin/knowledge/upload",
        data={"title": "X", "category": "Networking"},
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response_unauth.status_code == 401


def test_delete_and_reindex_require_admin(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    admin_headers = _admin_headers(client, db_session)
    employee_headers = _employee_headers(client, db_session)

    response = _upload(
        client,
        admin_headers,
        filename="notes.txt",
        content=b"Some content.",
        content_type="text/plain",
    )
    document_id = response.json()["id"]
    document_service.process_document(uuid.UUID(document_id), db=db_session)

    assert (
        client.delete(f"/api/admin/knowledge/{document_id}", headers=employee_headers).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/knowledge/{document_id}/reindex", headers=employee_headers
        ).status_code
        == 403
    )


def test_employee_can_view_ready_documents(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    admin_headers = _admin_headers(client, db_session)
    employee_headers = _employee_headers(client, db_session)

    response = _upload(
        client,
        admin_headers,
        filename="notes.txt",
        content=b"Readable content.",
        content_type="text/plain",
    )
    document_id = response.json()["id"]
    document_service.process_document(uuid.UUID(document_id), db=db_session)

    listing = client.get("/api/knowledge", headers=employee_headers)
    assert listing.status_code == 200
    assert any(doc["id"] == document_id for doc in listing.json())

    detail = client.get(f"/api/knowledge/{document_id}", headers=employee_headers)
    assert detail.status_code == 200
    assert "error_message" not in detail.json() or detail.json()["error_message"] is None


def test_employee_cannot_see_non_ready_documents(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(texts: list[str], *, client: object | None = None) -> list[list[float]]:
        raise embedding_service.EmbeddingGenerationError("simulated outage")

    monkeypatch.setattr(embedding_service, "generate_embeddings", _boom)

    admin_headers = _admin_headers(client, db_session)
    employee_headers = _employee_headers(client, db_session)

    response = _upload(
        client,
        admin_headers,
        filename="fails.txt",
        content=b"Will fail to embed.",
        content_type="text/plain",
    )
    document_id = response.json()["id"]
    document_service.process_document(uuid.UUID(document_id), db=db_session)

    listing = client.get("/api/knowledge", headers=employee_headers)
    assert all(doc["id"] != document_id for doc in listing.json())

    detail = client.get(f"/api/knowledge/{document_id}", headers=employee_headers)
    assert detail.status_code == 404

    admin_detail = client.get(f"/api/knowledge/{document_id}", headers=admin_headers)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["status"] == "FAILED"
    assert admin_detail.json()["error_message"]


# ---- Delete / reindex ----


def test_delete_document_removes_chunks_and_file(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="notes.txt",
        content=b"Delete me please.",
        content_type="text/plain",
    )
    document_id = uuid.UUID(response.json()["id"])
    document_service.process_document(document_id, db=db_session)

    document = document_service.get_visible_document(db_session, document_id, is_admin=True)
    assert document is not None
    storage_path = Path(document.storage_path)
    assert storage_path.exists()

    delete_response = client.delete(f"/api/admin/knowledge/{document_id}", headers=headers)
    assert delete_response.status_code == 204

    assert client.get(f"/api/knowledge/{document_id}", headers=headers).status_code == 404
    assert not storage_path.exists()
    remaining_chunks = db_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    ).all()
    assert remaining_chunks == []


def test_reindex_regenerates_chunks_and_bumps_version(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)
    response = _upload(
        client,
        headers,
        filename="notes.txt",
        content=b"Reindex me please.",
        content_type="text/plain",
    )
    document_id = uuid.UUID(response.json()["id"])
    document_service.process_document(document_id, db=db_session)

    before = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    assert before["version"] == 1

    reindex_response = client.post(f"/api/admin/knowledge/{document_id}/reindex", headers=headers)
    assert reindex_response.status_code == 202
    document_service.process_document(document_id, db=db_session)

    after = client.get(f"/api/knowledge/{document_id}", headers=headers).json()
    assert after["version"] == 2
    assert after["status"] == "READY"
    assert after["chunk_count"] >= 1


# ---- Search & filtering ----


def test_search_and_category_filter(
    client: TestClient, db_session: Session, fake_embeddings: None
) -> None:
    headers = _admin_headers(client, db_session)

    r1 = _upload(
        client,
        headers,
        filename="vpn.txt",
        content=b"VPN setup instructions.",
        content_type="text/plain",
        title="VPN Setup Guide",
        category="Networking",
    )
    r2 = _upload(
        client,
        headers,
        filename="mfa.txt",
        content=b"MFA enrollment instructions.",
        content_type="text/plain",
        title="MFA Setup Guide",
        category="Security",
    )
    document_service.process_document(uuid.UUID(r1.json()["id"]), db=db_session)
    document_service.process_document(uuid.UUID(r2.json()["id"]), db=db_session)

    by_category = client.get(
        "/api/knowledge", headers=headers, params={"category": "Security"}
    ).json()
    assert all(doc["category"] == "Security" for doc in by_category)
    assert any(doc["title"] == "MFA Setup Guide" for doc in by_category)
    assert all(doc["title"] != "VPN Setup Guide" for doc in by_category)

    by_search = client.get("/api/knowledge", headers=headers, params={"search": "VPN"}).json()
    assert any(doc["title"] == "VPN Setup Guide" for doc in by_search)
    assert all(doc["title"] != "MFA Setup Guide" for doc in by_search)


# ---- Real embedding API (integration; skipped unless a key is configured) ----


@pytest.mark.skipif(not get_settings().gemini_api_key, reason="GEMINI_API_KEY is not configured")
def test_generate_embeddings_against_real_gemini_api() -> None:
    vectors = embedding_service.generate_embeddings(["hello knowledge base"])
    assert len(vectors) == 1
    assert len(vectors[0]) == settings.embedding_dimensions
