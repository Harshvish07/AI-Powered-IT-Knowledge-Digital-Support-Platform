from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_authenticated_user
from app.core.database import get_db
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserPublic

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_current_user_profile(user: User = Depends(require_authenticated_user)) -> User:
    return user


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> list[User]:
    return user_repository.list_all(db)
