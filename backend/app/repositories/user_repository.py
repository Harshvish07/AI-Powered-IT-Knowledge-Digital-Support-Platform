import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    return db.scalar(stmt)


def list_all(db: Session, *, search: str | None = None, role: UserRole | None = None) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    stmt = stmt.order_by(User.created_at)
    return list(db.scalars(stmt))


def get_by_ids(db: Session, ids: set[uuid.UUID]) -> list[User]:
    if not ids:
        return []
    stmt = select(User).where(User.id.in_(ids))
    return list(db.scalars(stmt))


def count_all(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


def count_active(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.is_active)) or 0


def set_active(db: Session, user: User, *, is_active: bool) -> User:
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
