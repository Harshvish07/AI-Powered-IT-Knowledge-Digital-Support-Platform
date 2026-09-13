import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    return db.scalar(stmt)


def list_all(db: Session) -> list[User]:
    stmt = select(User).order_by(User.created_at)
    return list(db.scalars(stmt))


def create(
    db: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    role: UserRole = UserRole.EMPLOYEE,
) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=password_hash,
        full_name=full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
