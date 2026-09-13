import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_authenticated_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.schemas.user import UserActiveUpdate, UserPublic

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_current_user_profile(user: User = Depends(require_authenticated_user)) -> User:
    return user


@router.get("", response_model=list[UserPublic])
def list_users(
    search: str | None = None,
    role: UserRole | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[User]:
    return user_repository.list_all(db, search=search, role=role)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user_active_status(
    user_id: uuid.UUID,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    if user_id == admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_repository.set_active(db, user, is_active=payload.is_active)
