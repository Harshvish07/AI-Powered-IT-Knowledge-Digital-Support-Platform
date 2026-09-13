import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


def get_by_token_hash(db: Session, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return db.scalar(stmt)


def create(
    db: Session, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke(db: Session, token: RefreshToken, *, revoked_at: datetime) -> None:
    token.revoked_at = revoked_at
    db.add(token)
    db.commit()
