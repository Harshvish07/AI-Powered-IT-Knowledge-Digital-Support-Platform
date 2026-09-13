"""Registration, login, and refresh-token lifecycle. HTTP-agnostic: raises the
exceptions below, which the API layer maps to status codes.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories import refresh_token_repository, user_repository

settings = get_settings()


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AccountDisabledError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def register_user(db: Session, *, email: str, password: str, full_name: str) -> User:
    if user_repository.get_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(email)
    password_hash = hash_password(password)
    return user_repository.create(
        db,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=UserRole.EMPLOYEE,
    )


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = user_repository.get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise AccountDisabledError()
    return user


def issue_token_pair(db: Session, user: User) -> tuple[str, int, str, datetime]:
    """Returns (access_token, expires_in, raw_refresh_token, refresh_expires_at)."""
    access_token, expires_in = create_access_token(user.id, user.role.value)

    raw_refresh_token = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token_repository.create(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=expires_at,
    )
    return access_token, expires_in, raw_refresh_token, expires_at


def rotate_refresh_token(
    db: Session, raw_refresh_token: str
) -> tuple[User, str, int, str, datetime]:
    """Validates and revokes the presented refresh token, issuing a fresh pair.

    Returns (user, access_token, expires_in, new_raw_refresh_token, new_refresh_expires_at).
    """
    now = datetime.now(UTC)
    stored = refresh_token_repository.get_by_token_hash(db, hash_refresh_token(raw_refresh_token))
    if stored is None or stored.revoked_at is not None or stored.expires_at < now:
        raise InvalidRefreshTokenError()

    user = user_repository.get_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    refresh_token_repository.revoke(db, stored, revoked_at=now)

    access_token, expires_in, new_raw_refresh_token, new_expires_at = issue_token_pair(db, user)
    return user, access_token, expires_in, new_raw_refresh_token, new_expires_at


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    stored = refresh_token_repository.get_by_token_hash(db, hash_refresh_token(raw_refresh_token))
    if stored is not None and stored.revoked_at is None:
        refresh_token_repository.revoke(db, stored, revoked_at=datetime.now(UTC))
