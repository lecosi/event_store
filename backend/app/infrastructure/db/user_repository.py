from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from app.application.errors import EmailAlreadyRegisteredError
from app.domain.user import UserAccount
from app.infrastructure.db.mappers import user_to_domain
from app.infrastructure.db.models import User


class SqlUserRepository:
    """SQLModel implementation of the UserRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> UserAccount | None:
        row = self._session.get(User, user_id)
        return user_to_domain(row) if row else None

    def get_by_email(self, email: str) -> UserAccount | None:
        row = self._session.exec(select(User).where(User.email == email)).first()
        return user_to_domain(row) if row else None

    def list_page(self, page: int, size: int) -> tuple[list[UserAccount], int]:
        total = self._session.exec(select(func.count()).select_from(User)).one()
        rows = self._session.exec(
            select(User).order_by(col(User.id)).offset((page - 1) * size).limit(size)
        ).all()
        return [user_to_domain(row) for row in rows], total

    def add(self, user: UserAccount) -> UserAccount:
        row = User(
            email=user.email,
            full_name=user.full_name,
            password_hash=user.password_hash,
            role=user.role,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyRegisteredError(user.email) from exc
        self._session.refresh(row)
        return user_to_domain(row)

    def save(self, user: UserAccount) -> UserAccount:
        row = self._session.get(User, user.id)
        if row is None:
            raise LookupError(f"User {user.id} does not exist")
        row.email = user.email
        row.full_name = user.full_name
        row.role = user.role
        row.is_active = user.is_active
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyRegisteredError(user.email) from exc
        self._session.refresh(row)
        return user_to_domain(row)
