"""Development-only seed script: creates an admin user from environment variables.

Never wires in a hardcoded credential — SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD must be
set in the environment (e.g. in .env), and the script refuses to run when
ENVIRONMENT=production.

Usage:
    python -m app.scripts.seed_admin
    # or, via Docker Compose:
    docker compose exec backend python -m app.scripts.seed_admin
"""

import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories import user_repository
from app.utils.validation import validate_password_strength


def main() -> int:
    settings = get_settings()

    if settings.environment.lower() == "production":
        print("Refusing to run the admin seed script with ENVIRONMENT=production.")
        return 1

    if not settings.seed_admin_email or not settings.seed_admin_password:
        print("SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD must be set to seed an admin user.")
        return 1

    email = settings.seed_admin_email.strip().lower()

    try:
        validate_password_strength(settings.seed_admin_password)
    except ValueError as exc:
        print(f"SEED_ADMIN_PASSWORD does not meet the password policy: {exc}")
        return 1

    db = SessionLocal()
    try:
        if user_repository.get_by_email(db, email) is not None:
            print(f"Admin user '{email}' already exists; skipping.")
            return 0

        user_repository.create(
            db,
            email=email,
            password_hash=hash_password(settings.seed_admin_password),
            full_name=settings.seed_admin_full_name,
            role=UserRole.ADMIN,
        )
        print(f"Seeded admin user: {email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
