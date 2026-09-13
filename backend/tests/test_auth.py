from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories import user_repository
from tests.conftest import unique_email

settings = get_settings()

VALID_PASSWORD = "StrongPass1!"


def _register(client: TestClient, *, email: str | None = None, password: str = VALID_PASSWORD):
    return client.post(
        "/api/auth/register",
        json={
            "email": email or unique_email(),
            "password": password,
            "full_name": "Test User",
        },
    )


def _make_expired_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "role": "EMPLOYEE",
        "type": "access",
        "iat": datetime.now(UTC) - timedelta(minutes=30),
        "exp": datetime.now(UTC) - timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ---- Registration ----


def test_register_success(client: TestClient) -> None:
    email = unique_email()
    response = _register(client, email=email)

    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "password" not in body
    assert "password_hash" not in body

    me = client.get("/api/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == email
    assert me_body["full_name"] == "Test User"
    assert me_body["role"] == "EMPLOYEE"
    assert me_body["is_active"] is True
    assert "password" not in me_body
    assert "password_hash" not in me_body


def test_register_duplicate_email(client: TestClient) -> None:
    email = unique_email()
    first = _register(client, email=email)
    assert first.status_code == 201

    second = _register(client, email=email)
    assert second.status_code == 409


def test_register_invalid_password(client: TestClient) -> None:
    response = _register(client, password="weak")
    assert response.status_code == 422


def test_register_invalid_email_format(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": VALID_PASSWORD, "full_name": "Test User"},
    )
    assert response.status_code == 422


# ---- Login ----


def test_login_success(client: TestClient) -> None:
    email = unique_email()
    _register(client, email=email)

    response = client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert settings.refresh_cookie_name in response.cookies


def test_login_wrong_password(client: TestClient) -> None:
    email = unique_email()
    _register(client, email=email)

    response = client.post("/api/auth/login", json={"email": email, "password": "WrongPass1!"})
    assert response.status_code == 401


def test_login_nonexistent_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": unique_email(), "password": VALID_PASSWORD}
    )
    assert response.status_code == 401


# ---- Token validation ----


def test_valid_token_access(client: TestClient) -> None:
    register_response = _register(client)
    token = register_response.json()["access_token"]

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_expired_token(client: TestClient) -> None:
    register_response = _register(client)
    me_before = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {register_response.json()['access_token']}"},
    )
    user_id = me_before.json()["id"]

    expired_token = _make_expired_access_token(user_id)
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_unauthorized_access_no_token(client: TestClient) -> None:
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_invalid_token(client: TestClient) -> None:
    response = client.get("/api/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


# ---- RBAC ----


def test_employee_cannot_access_admin_endpoint(client: TestClient) -> None:
    register_response = _register(client)
    token = register_response.json()["access_token"]

    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_can_access_admin_endpoint(client: TestClient, db_session: Session) -> None:
    email = unique_email("admin")
    user_repository.create(
        db_session,
        email=email,
        password_hash=hash_password(VALID_PASSWORD),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )

    login_response = client.post(
        "/api/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ---- Refresh & logout ----


def test_refresh_rotates_token_and_old_one_becomes_invalid(client: TestClient) -> None:
    email = unique_email()
    _register(client, email=email)
    login_response = client.post(
        "/api/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    old_refresh_token = login_response.cookies[settings.refresh_cookie_name]

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()

    client.cookies.set(settings.refresh_cookie_name, old_refresh_token)
    reuse_response = client.post("/api/auth/refresh")
    assert reuse_response.status_code == 401


def test_refresh_without_cookie(client: TestClient) -> None:
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    email = unique_email()
    _register(client, email=email)
    client.post("/api/auth/login", json={"email": email, "password": VALID_PASSWORD})

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    refresh_after_logout = client.post("/api/auth/refresh")
    assert refresh_after_logout.status_code == 401
