import uuid

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserPublic(BaseModel):
    """A user's public profile — never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
