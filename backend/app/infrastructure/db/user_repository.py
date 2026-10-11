from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

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

    def list_all(self) -> list[UserAccount]:
        rows = self._session.exec(select(User).order_by(col(User.id))).all()
        return [_to_account(row) for row in rows]

    def list_page(self, page: int, size: int) -> tuple[list[UserAccount], int]:
        total = self._session.exec(select(func.count()).select_from(User)).one()
        rows = self._session.exec(
            select(User).order_by(col(User.id)).offset((page - 1) * size).limit(size)
        ).all()
        return [_to_account(row) for row in rows], total

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        row = User(email=email, password_hash=password_hash, role=role)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise EmailAlreadyRegisteredError(email) from exc
        self._session.refresh(row)
        return _to_account(row)

    def save(self, user: UserAccount) -> UserAccount:
        row = self._session.get(User, user.id)
        if row is None:
            raise LookupError(f"User {user.id} does not exist")
        row.role = user.role
        row.is_active = user.is_active
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return _to_account(row)
