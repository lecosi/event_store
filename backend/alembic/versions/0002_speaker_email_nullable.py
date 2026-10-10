"""speaker email nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09 21:10:00
"""
from collections.abc import Sequence

import sqlmodel

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "speaker",
        "email",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
        nullable=True,
    )
    # Existing rows used '' as "no email"; normalise (uq_speaker_email already exists since 0001).
    op.execute("UPDATE speaker SET email = NULL WHERE TRIM(email) = ''")
    op.execute("UPDATE speaker SET email = LOWER(TRIM(email)) WHERE email IS NOT NULL")


def downgrade() -> None:
    op.execute("UPDATE speaker SET email = '' WHERE email IS NULL")
    op.alter_column(
        "speaker",
        "email",
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
        nullable=False,
    )
