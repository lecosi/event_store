from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.application.errors import EmailAlreadyRegisteredError
from app.domain.enums import Role
from app.domain.user import UserAccount
from app.infrastructure.db.models import User


def _to_account(row: User) -> UserAccount:
    return UserAccount(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        role=row.role,
        is_active=row.is_active,
    )


class SqlUserRepository:
    """SQLModel implementation of the UserRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> UserAccount | None:
        row = self._session.get(User, user_id)
        return _to_account(row) if row else None

    def get_by_email(self, email: str) -> UserAccount | None:
        row = self._session.exec(select(User).where(User.email == email)).first()
        return _to_account(row) if row else None

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        row = User(email=email, password_hash=password_hash, role=role)
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise EmailAlreadyRegisteredError(email) from exc
        self._session.refresh(row)
        return _to_account(row)
