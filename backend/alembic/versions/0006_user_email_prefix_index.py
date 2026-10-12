"""index serving case-insensitive email prefix search

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-12 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_users_email_lower_prefix"


def upgrade() -> None:
    op.create_index(INDEX_NAME, "users", [sa.text("lower(email) text_pattern_ops")])


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="users")
