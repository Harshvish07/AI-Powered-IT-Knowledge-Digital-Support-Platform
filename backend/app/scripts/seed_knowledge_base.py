"""Seeds the knowledge base with realistic demo IT documentation.

Safe to re-run: documents are matched by title and skipped if they already
exist. Requires at least one ADMIN user to exist already (see
app/scripts/seed_admin.py). Runs the real ingestion pipeline synchronously
(not as a background task, since there's no running app here), so it also
doubles as an end-to-end check of extraction/chunking/embedding/storage.

Without OPENAI_API_KEY configured, each document is still created but ends up
FAILED at the embedding step — exactly like any other upload would.

Usage:
    python -m app.scripts.seed_knowledge_base
"""

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.repositories import document_repository
from app.services import document_service

SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "seed_data" / "knowledge_base"

DOCUMENTS = [
    {
        "filename": "vpn_setup_guide.md",
        "title": "VPN Setup Guide",
        "category": "Networking",
        "description": "How to install, configure, and troubleshoot the company VPN client.",
    },
    {
        "filename": "password_reset_procedure.md",
        "title": "Password Reset Procedure",
        "category": "Account Management",
        "description": "How to reset a forgotten or expiring company account password.",
    },
    {
        "filename": "wifi_configuration_guide.md",
        "title": "Wi-Fi Configuration Guide",
        "category": "Networking",
        "description": "Connecting company and personal devices to office Wi-Fi networks.",
    },
    {
        "filename": "github_access_policy.md",
        "title": "GitHub Access Policy",
        "category": "Policy",
        "description": "How GitHub organization access is requested, granted, and revoked.",
    },
    {
        "filename": "laptop_lost_stolen_procedure.md",
        "title": "Laptop Lost/Stolen Procedure",
        "category": "Security",
        "description": "Immediate steps to take if a company laptop is lost or stolen.",
    },
    {
        "filename": "software_installation_policy.md",
        "title": "Software Installation Policy",
        "category": "Policy",
        "description": (
            "What software can be installed on company devices, and how to request more."
        ),
    },
    {
        "filename": "remote_work_security_policy.md",
        "title": "Remote Work Security Policy",
        "category": "Security",
        "description": "Minimum security expectations for working outside a company office.",
    },
    {
        "filename": "mfa_setup_guide.md",
        "title": "MFA Setup Guide",
        "category": "Security",
        "description": (
            "Enrolling in and using multi-factor authentication for your company account."
        ),
    },
]


def _find_seed_admin(db: Session) -> User | None:
    stmt = select(User).where(User.role == UserRole.ADMIN).order_by(User.created_at)
    return db.scalars(stmt).first()


def main() -> int:
    db = SessionLocal()
    try:
        admin = _find_seed_admin(db)
        if admin is None:
            print(
                "No ADMIN user exists yet — run the admin seed script first "
                "(python -m app.scripts.seed_admin)."
            )
            return 1

        existing_titles = {doc.title for doc in document_repository.list_documents(db)}

        for entry in DOCUMENTS:
            if entry["title"] in existing_titles:
                print(f"Skipping '{entry['title']}' — already exists.")
                continue

            file_bytes = (SEED_DATA_DIR / entry["filename"]).read_bytes()

            document = document_service.create_document(
                db,
                title=entry["title"],
                original_filename=entry["filename"],
                description=entry["description"],
                category=entry["category"],
                uploaded_by=admin.id,
                file_bytes=file_bytes,
            )
            print(f"Created '{entry['title']}' ({document.id}); processing...")
            document_service.process_document(document.id)

            db.expire_all()
            refreshed = document_repository.get_by_id(db, document.id)
            print(f"  -> status: {refreshed.status if refreshed else 'UNKNOWN'}")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
