"""mandatory user full name

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FULL_NAME_LENGTH = 200


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("full_name", sa.String(length=_FULL_NAME_LENGTH), nullable=True)
    )
    # Existing accounts have no name yet: use the email local part until the user edits it.
    op.execute(
        "UPDATE users SET full_name = "
        f"LEFT(COALESCE(NULLIF(SPLIT_PART(email, '@', 1), ''), email), {_FULL_NAME_LENGTH})"
    )
    op.alter_column("users", "full_name", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "full_name")
