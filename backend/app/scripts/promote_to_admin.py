"""Promotes an existing user to the ADMIN role. Unlike seed_admin.py, this
works in every environment, including production — it never handles a
plaintext password (the user must have already registered normally through
the public API), so there's no secret to protect and no reason to refuse to
run in production. This is the intended way to create the first admin
account on a production deployment: have that person register a normal
account through the app, then run this script with direct access to the
production environment (e.g. `docker compose exec backend ...`, which only
someone with deploy access can already do).

Usage:
    python -m app.scripts.promote_to_admin someone@example.com
    # or, via Docker Compose:
    docker compose exec backend python -m app.scripts.promote_to_admin someone@example.com
"""

import sys

from app.core.database import SessionLocal
from app.models.user import UserRole
from app.repositories import user_repository


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python -m app.scripts.promote_to_admin <email>")
        return 1

    email = argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = user_repository.get_by_email(db, email)
        if user is None:
            print(f"No user found with email '{email}'. They must register first.")
            return 1
        if user.role == UserRole.ADMIN:
            print(f"'{email}' is already an admin; nothing to do.")
            return 0

        user.role = UserRole.ADMIN
        db.add(user)
        db.commit()
        print(f"Promoted '{email}' to ADMIN.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
