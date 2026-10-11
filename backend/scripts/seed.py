"""Create (or promote) the administrator account.

Usage (from ``backend/``):  ``python -m scripts.seed``
Credentials come from ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD``.
"""

import os
import sys

from sqlmodel import Session

from app.application.admin_seed import ensure_admin
from app.infrastructure.db.session import get_engine
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.user_repository import SqlUserRepository
from app.infrastructure.security.password_hasher import Argon2PasswordHasher


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be set", file=sys.stderr)
        return 1
    with Session(get_engine()) as session:
        admin = ensure_admin(
            SqlUserRepository(session),
            Argon2PasswordHasher(),
            SqlUnitOfWork(session),
            email,
            password,
        )
    print(f"Admin ready: {admin.email} (id={admin.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
