"""Password hashing, JWT access tokens, and opaque refresh tokens."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

settings = get_settings()
_password_hasher = PasswordHasher()


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or has the wrong type."""


# ---- Passwords ----


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ---- JWT access tokens ----


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire_delta = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expire_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expire_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid") from exc

    if payload.get("type") != "access":
        raise InvalidTokenError("Token is not an access token")
    return payload


# ---- Opaque refresh tokens ----
# Stored server-side as a SHA-256 hash so a database leak doesn't hand out
# usable tokens; a fast hash is appropriate here since the token itself is a
# high-entropy random value, not a user-chosen secret.


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
