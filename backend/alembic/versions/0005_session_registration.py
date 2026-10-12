"""session registrations with per-session capacity

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-11 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_registration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "session_id", name="uq_session_registration_user_session"),
    )
    op.create_index(
        op.f("ix_session_registration_user_id"), "session_registration", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_session_registration_session_id"),
        "session_registration",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_registration_session_id"), table_name="session_registration")
    op.drop_index(op.f("ix_session_registration_user_id"), table_name="session_registration")
    op.drop_table("session_registration")
