"""check constraints and ON DELETE CASCADE for event children

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09 21:40:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# PostgreSQL default names for the unnamed FKs created in 0001.
_FKS = [
    ("session", "session_event_id_fkey"),
    ("registration", "registration_event_id_fkey"),
]


def upgrade() -> None:
    for table in ("event", "session"):
        op.create_check_constraint(f"ck_{table}_capacity_positive", table, "capacity >= 1")
        op.create_check_constraint(f"ck_{table}_dates_order", table, "end_at > start_at")
    for table, name in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "event", ["event_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    for table, name in _FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, "event", ["event_id"], ["id"])
    for table in ("event", "session"):
        op.drop_constraint(f"ck_{table}_dates_order", table, type_="check")
        op.drop_constraint(f"ck_{table}_capacity_positive", table, type_="check")
