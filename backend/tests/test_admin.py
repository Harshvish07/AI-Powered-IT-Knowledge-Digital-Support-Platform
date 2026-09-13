import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.conversation import Conversation
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.models.message import Message, MessageRole
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.repositories import user_repository
from tests.conftest import unique_email

VALID_PASSWORD = "StrongPass1!"


# ---- Fixtures / helpers ----


def _create_user(
    db: Session,
    *,
    role: UserRole = UserRole.EMPLOYEE,
    full_name: str = "Admin Test User",
) -> User:
    return user_repository.create(
        db,
        email=unique_email("admin-test"),
        password_hash=hash_password(VALID_PASSWORD),
        full_name=full_name,
        role=role,
    )


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient, db_session: Session) -> tuple[dict[str, str], User]:
    user = _create_user(db_session, role=UserRole.ADMIN)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}, user


def _employee_headers(client: TestClient, db_session: Session) -> tuple[dict[str, str], User]:
    user = _create_user(db_session, role=UserRole.EMPLOYEE)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}, user


def _create_document(
    db: Session, *, status: DocumentStatus = DocumentStatus.READY, category: str = "Test"
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        title=f"Doc {uuid.uuid4().hex[:8]}",
        filename="doc.md",
        description=None,
        category=category,
        uploaded_by=None,
        status=status,
        version=1,
        storage_path=f"unused/{uuid.uuid4()}.md",
        mime_type="text/markdown",
        file_size_bytes=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _create_ticket(
    db: Session,
    *,
    created_by: uuid.UUID,
    title: str = "Test ticket",
    status: TicketStatus = TicketStatus.OPEN,
    category: TicketCategory = TicketCategory.OTHER,
    priority: TicketPriority = TicketPriority.LOW,
) -> Ticket:
    ticket = Ticket(
        title=title,
        description="Test description",
        category=category,
        priority=priority,
        status=status,
        created_by=created_by,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def _create_conversation_with_messages(
    db: Session, *, user_id: uuid.UUID, question_count: int = 1
) -> Conversation:
    conversation = Conversation(user_id=user_id, title="Test conversation")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    for i in range(question_count):
        db.add(Message(conversation_id=conversation.id, role=MessageRole.USER, content=f"Q{i}"))
        db.add(
            Message(conversation_id=conversation.id, role=MessageRole.ASSISTANT, content=f"A{i}")
        )
    db.commit()
    db.refresh(conversation)
    return conversation


# ---- Dashboard metrics ----


def test_unauthenticated_cannot_access_dashboard(client: TestClient) -> None:
    assert client.get("/api/admin/dashboard").status_code == 401


def test_employee_cannot_access_dashboard(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    assert client.get("/api/admin/dashboard", headers=headers).status_code == 403


def test_dashboard_metrics_reflect_real_data(client: TestClient, db_session: Session) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    _, employee = _employee_headers(client, db_session)

    _create_document(db_session, status=DocumentStatus.READY)
    _create_document(db_session, status=DocumentStatus.FAILED)
    _create_ticket(db_session, created_by=employee.id, status=TicketStatus.OPEN)
    _create_ticket(db_session, created_by=employee.id, status=TicketStatus.IN_PROGRESS)
    _create_ticket(db_session, created_by=employee.id, status=TicketStatus.RESOLVED)
    _create_conversation_with_messages(db_session, user_id=employee.id, question_count=2)

    response = client.get("/api/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()

    # >= rather than == : this runs against the shared dev database, which may
    # already hold real users/documents/tickets from prior manual use.
    assert body["total_users"] >= 2
    assert body["active_users"] >= 2
    assert body["total_documents"] >= 2
    assert body["ready_documents"] >= 1
    assert body["failed_documents"] >= 1
    assert body["total_tickets"] >= 3
    assert body["open_tickets"] >= 1
    assert body["in_progress_tickets"] >= 1
    assert body["resolved_tickets"] >= 1
    assert body["ai_questions"] >= 2
    assert body["tickets_by_status"]["OPEN"] >= 1
    assert body["tickets_by_status"]["IN_PROGRESS"] >= 1
    assert body["tickets_by_category"]["OTHER"] >= 1
    assert body["documents_by_status"]["READY"] >= 1
    assert body["documents_by_status"]["FAILED"] >= 1
    assert len(body["ai_questions_by_day"]) == 14
    assert sum(day["count"] for day in body["ai_questions_by_day"]) >= 2


# ---- Ticket filters (admin) ----


def test_admin_ticket_filters_by_status_category_priority_and_search(
    client: TestClient, db_session: Session
) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    _, employee = _employee_headers(client, db_session)

    matching = _create_ticket(
        db_session,
        created_by=employee.id,
        title="VPN outage across the building",
        status=TicketStatus.OPEN,
        category=TicketCategory.NETWORK,
        priority=TicketPriority.CRITICAL,
    )
    other = _create_ticket(
        db_session,
        created_by=employee.id,
        title="Printer jam on 3rd floor",
        status=TicketStatus.CLOSED,
        category=TicketCategory.HARDWARE,
        priority=TicketPriority.LOW,
    )

    response = client.get(
        "/api/admin/tickets",
        headers=admin_headers,
        params={
            "status": "OPEN",
            "category": "NETWORK",
            "priority": "CRITICAL",
            "search": "VPN",
        },
    )
    assert response.status_code == 200
    ids = {t["id"] for t in response.json()}
    assert str(matching.id) in ids
    assert str(other.id) not in ids


# ---- User management ----


def test_admin_can_search_and_filter_users_by_role(client: TestClient, db_session: Session) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    target = _create_user(db_session, role=UserRole.EMPLOYEE, full_name="Zzyzx Search Target")
    _create_user(db_session, role=UserRole.EMPLOYEE, full_name="Someone Else Entirely")

    search_response = client.get("/api/users", headers=admin_headers, params={"search": "Zzyzx"})
    assert search_response.status_code == 200
    emails = {u["email"] for u in search_response.json()}
    assert target.email in emails
    assert len(search_response.json()) == 1

    role_response = client.get("/api/users", headers=admin_headers, params={"role": "ADMIN"})
    assert role_response.status_code == 200
    assert all(u["role"] == "ADMIN" for u in role_response.json())
    assert len(role_response.json()) >= 1


def test_employee_cannot_search_users(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    assert client.get("/api/users", headers=headers).status_code == 403


def test_admin_can_deactivate_and_reactivate_a_user(
    client: TestClient, db_session: Session
) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    target = _create_user(db_session, role=UserRole.EMPLOYEE)

    deactivate = client.patch(
        f"/api/users/{target.id}", headers=admin_headers, json={"is_active": False}
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    reactivate = client.patch(
        f"/api/users/{target.id}", headers=admin_headers, json={"is_active": True}
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True


def test_deactivated_user_is_immediately_locked_out(
    client: TestClient, db_session: Session
) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    target = _create_user(db_session, role=UserRole.EMPLOYEE)
    target_token = _login(client, target.email)

    client.patch(f"/api/users/{target.id}", headers=admin_headers, json={"is_active": False})

    # An already-issued access token stops working immediately (require_authenticated_user
    # re-checks is_active on every request), not just on the next login attempt.
    me_response = client.get("/api/users/me", headers={"Authorization": f"Bearer {target_token}"})
    assert me_response.status_code == 401

    login_response = client.post(
        "/api/auth/login", json={"email": target.email, "password": VALID_PASSWORD}
    )
    assert login_response.status_code == 403


def test_admin_cannot_deactivate_own_account(client: TestClient, db_session: Session) -> None:
    admin_headers, admin_user = _admin_headers(client, db_session)
    response = client.patch(
        f"/api/users/{admin_user.id}", headers=admin_headers, json={"is_active": False}
    )
    assert response.status_code == 400

    # Confirm the account is genuinely untouched, not just an error with a side effect.
    me = client.get("/api/users/me", headers=admin_headers)
    assert me.json()["is_active"] is True


def test_employee_cannot_change_active_status(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    target = _create_user(db_session, role=UserRole.EMPLOYEE)
    response = client.patch(f"/api/users/{target.id}", headers=headers, json={"is_active": False})
    assert response.status_code == 403


def test_deactivate_unknown_user_returns_404(client: TestClient, db_session: Session) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    response = client.patch(
        f"/api/users/{uuid.uuid4()}", headers=admin_headers, json={"is_active": False}
    )
    assert response.status_code == 404


# ---- AI conversations (admin) ----


def test_employee_cannot_list_admin_conversations(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    assert client.get("/api/admin/conversations", headers=headers).status_code == 403


def test_unauthenticated_cannot_list_admin_conversations(client: TestClient) -> None:
    assert client.get("/api/admin/conversations").status_code == 401


def test_admin_can_list_conversation_metadata_without_message_content(
    client: TestClient, db_session: Session
) -> None:
    admin_headers, _ = _admin_headers(client, db_session)
    _, employee = _employee_headers(client, db_session)
    conversation = _create_conversation_with_messages(db_session, user_id=employee.id)

    response = client.get("/api/admin/conversations", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()

    match = next(c for c in body if c["id"] == str(conversation.id))
    assert match["user_id"] == str(employee.id)
    assert match["user_email"] == employee.email
    assert match["user_name"] == employee.full_name
    assert match["message_count"] == 2
    assert "content" not in match
    assert "messages" not in match
