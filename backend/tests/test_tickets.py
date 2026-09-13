import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories import user_repository
from tests.conftest import unique_email

VALID_PASSWORD = "StrongPass1!"


# ---- Fixtures / helpers ----


def _create_user(db: Session, *, role: UserRole = UserRole.EMPLOYEE) -> User:
    return user_repository.create(
        db,
        email=unique_email("tix"),
        password_hash=hash_password(VALID_PASSWORD),
        full_name="Ticket Test User",
        role=role,
    )


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _employee_headers(client: TestClient, db_session: Session) -> tuple[dict[str, str], User]:
    user = _create_user(db_session, role=UserRole.EMPLOYEE)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}, user


def _admin_headers(client: TestClient, db_session: Session) -> tuple[dict[str, str], User]:
    user = _create_user(db_session, role=UserRole.ADMIN)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}, user


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "VPN keeps disconnecting",
        "description": "The VPN client disconnects every few minutes on Windows 11.",
        "category": "NETWORK",
        "priority": "HIGH",
    }
    payload.update(overrides)
    return payload


def _create_ticket(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post("/api/tickets", headers=headers, json=_valid_payload(**overrides))
    assert response.status_code == 201
    return response.json()


# ---- 1. Create ticket ----


def test_create_ticket_success(client: TestClient, db_session: Session) -> None:
    headers, user = _employee_headers(client, db_session)
    body = _create_ticket(client, headers)

    assert body["title"] == "VPN keeps disconnecting"
    assert body["category"] == "NETWORK"
    assert body["priority"] == "HIGH"
    assert body["status"] == "OPEN"
    assert body["created_by"] == str(user.id)
    assert body["assigned_to"] is None
    assert body["comments"] == []
    assert uuid.UUID(body["id"])


# ---- 2. Validation ----


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"description": ""},
        {"category": "NOT_A_CATEGORY"},
        {"priority": "NOT_A_PRIORITY"},
    ],
)
def test_create_ticket_validation_errors(
    client: TestClient, db_session: Session, overrides: dict[str, object]
) -> None:
    headers, _ = _employee_headers(client, db_session)
    response = client.post("/api/tickets", headers=headers, json=_valid_payload(**overrides))
    assert response.status_code == 422


def test_create_ticket_missing_fields(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    response = client.post("/api/tickets", headers=headers, json={"title": "Only a title"})
    assert response.status_code == 422


# ---- 3. Employee ticket visibility ----


def test_employee_sees_only_own_tickets(client: TestClient, db_session: Session) -> None:
    headers_a, _ = _employee_headers(client, db_session)
    headers_b, _ = _employee_headers(client, db_session)

    _create_ticket(client, headers_a, title="A's ticket")
    _create_ticket(client, headers_b, title="B's ticket")

    response = client.get("/api/tickets", headers=headers_a)
    assert response.status_code == 200
    titles = {ticket["title"] for ticket in response.json()}
    assert titles == {"A's ticket"}


def test_employee_can_filter_own_tickets(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    _create_ticket(client, headers, title="Low priority thing", priority="LOW")
    _create_ticket(client, headers, title="Critical outage", priority="CRITICAL")

    response = client.get("/api/tickets?priority=CRITICAL", headers=headers)
    assert response.status_code == 200
    titles = {ticket["title"] for ticket in response.json()}
    assert titles == {"Critical outage"}


# ---- 4. Employee cannot access another user's ticket ----


def test_employee_cannot_access_another_users_ticket(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, _ = _employee_headers(client, db_session)
    other_headers, _ = _employee_headers(client, db_session)

    ticket = _create_ticket(client, owner_headers)
    ticket_id = ticket["id"]

    assert client.get(f"/api/tickets/{ticket_id}", headers=other_headers).status_code == 404
    assert (
        client.post(
            f"/api/tickets/{ticket_id}/comments", headers=other_headers, json={"content": "Hi"}
        ).status_code
        == 404
    )
    # The owner can still reach it — confirms this is an ownership check, not a broken route.
    assert client.get(f"/api/tickets/{ticket_id}", headers=owner_headers).status_code == 200


# ---- 5. Admin can view all tickets ----


def test_admin_can_view_all_tickets(client: TestClient, db_session: Session) -> None:
    headers_a, _ = _employee_headers(client, db_session)
    headers_b, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)

    _create_ticket(client, headers_a, title="A's ticket")
    _create_ticket(client, headers_b, title="B's ticket")

    response = client.get("/api/admin/tickets", headers=admin_headers)
    assert response.status_code == 200
    titles = {ticket["title"] for ticket in response.json()}
    assert {"A's ticket", "B's ticket"}.issubset(titles)


def test_admin_can_view_any_ticket_detail(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)

    ticket = _create_ticket(client, employee_headers)
    response = client.get(f"/api/tickets/{ticket['id']}", headers=admin_headers)
    assert response.status_code == 200


def test_employee_cannot_use_admin_endpoints(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    assert client.get("/api/admin/tickets", headers=employee_headers).status_code == 403
    assert (
        client.patch(
            f"/api/admin/tickets/{ticket['id']}",
            headers=employee_headers,
            json={"status": "CLOSED"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/admin/tickets/{ticket['id']}/assign", headers=employee_headers, json={}
        ).status_code
        == 403
    )


# ---- 6. Admin assignment ----


def test_admin_can_assign_ticket(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, admin_user = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    response = client.post(
        f"/api/admin/tickets/{ticket['id']}/assign",
        headers=admin_headers,
        json={"assigned_to": str(admin_user.id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_to"] == str(admin_user.id)
    assert body["assigned_to_name"] == admin_user.full_name

    # Employee re-fetching their own ticket now sees the updated assignment.
    updated = client.get(f"/api/tickets/{ticket['id']}", headers=employee_headers)
    assert updated.json()["assigned_to"] == str(admin_user.id)


def test_admin_assign_to_unknown_user_is_rejected(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    response = client.post(
        f"/api/admin/tickets/{ticket['id']}/assign",
        headers=admin_headers,
        json={"assigned_to": str(uuid.uuid4())},
    )
    assert response.status_code == 422


# ---- 7. Status update ----


def test_admin_can_update_status(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    response = client.patch(
        f"/api/admin/tickets/{ticket['id']}", headers=admin_headers, json={"status": "IN_PROGRESS"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"

    # Employee sees the status change reflected on their own ticket.
    updated = client.get(f"/api/tickets/{ticket['id']}", headers=employee_headers)
    assert updated.json()["status"] == "IN_PROGRESS"


def test_update_requires_at_least_one_field(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    response = client.patch(f"/api/admin/tickets/{ticket['id']}", headers=admin_headers, json={})
    assert response.status_code == 422


# ---- 8. Priority update ----


def test_admin_can_update_priority(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, _ = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers, priority="LOW")

    response = client.patch(
        f"/api/admin/tickets/{ticket['id']}", headers=admin_headers, json={"priority": "CRITICAL"}
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "CRITICAL"


# ---- 9. Comments ----


def test_employee_can_comment_on_own_ticket(client: TestClient, db_session: Session) -> None:
    headers, user = _employee_headers(client, db_session)
    ticket = _create_ticket(client, headers)

    response = client.post(
        f"/api/tickets/{ticket['id']}/comments", headers=headers, json={"content": "Any update?"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Any update?"
    assert body["user_id"] == str(user.id)
    assert body["author_name"] == user.full_name

    detail = client.get(f"/api/tickets/{ticket['id']}", headers=headers)
    assert len(detail.json()["comments"]) == 1


def test_admin_can_comment_on_any_ticket(client: TestClient, db_session: Session) -> None:
    employee_headers, _ = _employee_headers(client, db_session)
    admin_headers, admin_user = _admin_headers(client, db_session)
    ticket = _create_ticket(client, employee_headers)

    response = client.post(
        f"/api/tickets/{ticket['id']}/comments",
        headers=admin_headers,
        json={"content": "We're looking into this."},
    )
    assert response.status_code == 201
    assert response.json()["author_name"] == admin_user.full_name


def test_empty_comment_is_rejected(client: TestClient, db_session: Session) -> None:
    headers, _ = _employee_headers(client, db_session)
    ticket = _create_ticket(client, headers)

    response = client.post(
        f"/api/tickets/{ticket['id']}/comments", headers=headers, json={"content": "   "}
    )
    assert response.status_code == 422


# ---- 10. Unauthorized access ----


def test_unauthenticated_cannot_access_tickets(client: TestClient) -> None:
    assert client.post("/api/tickets", json=_valid_payload()).status_code == 401
    assert client.get("/api/tickets").status_code == 401
    assert client.get(f"/api/tickets/{uuid.uuid4()}").status_code == 401
    assert client.get("/api/admin/tickets").status_code == 401
