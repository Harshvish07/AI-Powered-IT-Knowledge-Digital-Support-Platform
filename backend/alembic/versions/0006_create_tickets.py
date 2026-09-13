"""create tickets and ticket_comments tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ticket_category_enum = postgresql.ENUM(
    "HARDWARE",
    "SOFTWARE",
    "NETWORK",
    "ACCOUNT_ACCESS",
    "SECURITY",
    "OTHER",
    name="ticket_category",
    create_type=False,
)
ticket_priority_enum = postgresql.ENUM(
    "LOW", "MEDIUM", "HIGH", "CRITICAL", name="ticket_priority", create_type=False
)
ticket_status_enum = postgresql.ENUM(
    "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="ticket_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "HARDWARE", "SOFTWARE", "NETWORK", "ACCOUNT_ACCESS", "SECURITY", "OTHER",
        name="ticket_category",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "LOW", "MEDIUM", "HIGH", "CRITICAL", name="ticket_priority"
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="ticket_status"
    ).create(bind, checkfirst=True)

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", ticket_category_enum, nullable=False),
        sa.Column("priority", ticket_priority_enum, nullable=False),
        sa.Column("status", ticket_status_enum, nullable=False, server_default="OPEN"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_created_by", "tickets", ["created_by"])
    op.create_index("ix_tickets_assigned_to", "tickets", ["assigned_to"])

    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "ticket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ticket_comments_ticket_id", "ticket_comments", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")

    op.drop_index("ix_tickets_assigned_to", table_name="tickets")
    op.drop_index("ix_tickets_created_by", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_table("tickets")

    ticket_status_enum.drop(op.get_bind(), checkfirst=True)
    ticket_priority_enum.drop(op.get_bind(), checkfirst=True)
    ticket_category_enum.drop(op.get_bind(), checkfirst=True)
