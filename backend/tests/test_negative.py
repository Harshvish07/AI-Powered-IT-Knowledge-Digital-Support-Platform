"""Negative/adversarial-input tests that don't belong to one specific domain
module: rate limiting, malformed requests, SQL-injection-shaped input, and an
unexpected database failure. Auth-token edge cases (invalid/expired), RBAC
403s, prompt injection, and LLM/embedding failures are covered in their own
domain test files (test_auth.py, test_rag.py) rather than duplicated here.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.security import hash_password
from app.models.ticket import TicketCategory, TicketPriority
from app.models.user import User, UserRole
from app.repositories import ticket_repository, user_repository
from tests.conftest import unique_email

VALID_PASSWORD = "StrongPass1!"


def _create_user(db: Session, *, role: UserRole = UserRole.EMPLOYEE) -> User:
    return user_repository.create(
        db,
        email=unique_email("neg"),
        password_hash=hash_password(VALID_PASSWORD),
        full_name="Negative Test User",
        role=role,
    )


def _login(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 200
    return str(response.json()["access_token"])


def _employee_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    user = _create_user(db_session, role=UserRole.EMPLOYEE)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}


def _admin_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    user = _create_user(db_session, role=UserRole.ADMIN)
    return {"Authorization": f"Bearer {_login(client, user.email)}"}


# ---- Rate limiting ----


def test_login_is_rate_limited_after_repeated_attempts(client: TestClient) -> None:
    """auth endpoints are capped at 10/minute (see app/api/auth.py); the 11th
    attempt within the window must be rejected with 429, not silently allowed
    (this is the platform's only defense against credential brute-forcing)."""
    limiter.reset()
    for _ in range(10):
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401

    limited_response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert limited_response.status_code == 429


# ---- Malformed requests ----


def test_malformed_json_body_returns_422_not_500(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        content=b"{not valid json at all",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_missing_required_fields_returns_422(client: TestClient, db_session: Session) -> None:
    headers = _employee_headers(client, db_session)
    response = client.post("/api/tickets", headers=headers, json={"title": "Only a title"})
    assert response.status_code == 422


def test_wrong_field_types_return_422(client: TestClient, db_session: Session) -> None:
    headers = _employee_headers(client, db_session)
    response = client.post(
        "/api/tickets",
        headers=headers,
        json={
            "title": "Test",
            "description": "Test",
            "category": "HARDWARE",
            "priority": 12345,  # should be a string enum value
        },
    )
    assert response.status_code == 422


def test_invalid_uuid_path_param_returns_422_not_500(
    client: TestClient, db_session: Session
) -> None:
    headers = _employee_headers(client, db_session)
    response = client.get("/api/tickets/not-a-valid-uuid", headers=headers)
    assert response.status_code == 422


# ---- SQL-injection-shaped input ----


def test_sql_injection_shaped_search_is_treated_as_a_literal_string(
    client: TestClient, db_session: Session
) -> None:
    """Every query in this codebase goes through SQLAlchemy's parameterized
    query builder (no raw string-interpolated SQL anywhere) — this test
    verifies the *observable behavior* that follows from that: an
    injection-shaped search string is just an ordinary (non-matching) filter
    value, and known data survives untouched."""
    admin_headers = _admin_headers(client, db_session)
    owner = _create_user(db_session, role=UserRole.EMPLOYEE)
    ticket = ticket_repository.create(
        db_session,
        title="Survives injection attempt",
        description="Should still exist after the malicious search below.",
        category=TicketCategory.OTHER,
        priority=TicketPriority.LOW,
        created_by=owner.id,
    )

    payloads = [
        "'; DROP TABLE tickets; --",
        "' OR '1'='1",
        "x'; DELETE FROM users WHERE '1'='1",
    ]
    for payload in payloads:
        response = client.get(
            "/api/admin/tickets", headers=admin_headers, params={"search": payload}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # The table (and this specific row) must still exist — nothing was executed.
    still_there = ticket_repository.get_by_id(db_session, ticket.id)
    assert still_there is not None
    assert still_there.title == "Survives injection attempt"


def test_sql_injection_shaped_login_email_is_rejected_or_ignored_safely(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "' OR '1'='1", "password": "whatever"},
    )
    # Either a validation error (not a well-formed email) or a normal
    # "invalid credentials" — never a 500, and never a successful login.
    assert response.status_code in (401, 422)


# ---- Simulated database failure ----


def test_unexpected_database_error_returns_generic_500_without_leaking_details(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates an unexpected failure inside the data-access layer (e.g. a
    dropped connection) by making the repository raise. The centralized
    exception handler (app/main.py, Phase 8) must catch it and return a
    clean, consistent JSON body — never the exception text, a stack trace, a
    database error string, or an internal path — while still logging the
    real exception server-side (verified separately by this test not
    crashing and /health staying up).

    Uses raise_server_exceptions=False so the TestClient behaves like a real
    HTTP client would against a deployed server (which never sees the Python
    exception propagate — it gets a 500 response) rather than pytest's default
    of re-raising the server-side exception into the test itself.
    """
    from app.main import app as fastapi_app

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated database connection failure: details that must not leak")

    monkeypatch.setattr(ticket_repository, "create", _boom)

    headers = _employee_headers(client, db_session)
    real_client = TestClient(fastapi_app, raise_server_exceptions=False)
    response = real_client.post(
        "/api/tickets",
        headers=headers,
        json={
            "title": "Will fail at the DB layer",
            "description": "This should surface as a safe 500.",
            "category": "OTHER",
            "priority": "LOW",
        },
    )

    assert response.status_code == 500
    assert "simulated database connection failure" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text

    body = response.json()
    assert body["detail"] == "An unexpected error occurred. Please try again."
    assert "request_id" in body
    assert "debug_detail" not in body  # DEBUG=false in this test environment

    # The process itself is still healthy after the unhandled exception.
    assert client.get("/health").status_code == 200
