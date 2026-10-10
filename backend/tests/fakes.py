"""In-memory fakes of the application ports, for DB-free unit tests."""

from app.application.errors import EmailAlreadyRegisteredError, InvalidTokenError
from app.domain.enums import Role
from app.domain.user import UserAccount


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, UserAccount] = {}

    def get_by_id(self, user_id: int) -> UserAccount | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> UserAccount | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        if self.get_by_email(email):
            raise EmailAlreadyRegisteredError(email)
        user = UserAccount(
            email=email, password_hash=password_hash, role=role, id=len(self._by_id) + 1
        )
        self._by_id[user.id] = user
        return user


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{password}"


class FakeTokenService:
    def create_access_token(self, user_id: int) -> str:
        return f"token-{user_id}"

    def read_subject(self, token: str) -> int:
        if not token.startswith("token-"):
            raise InvalidTokenError
        return int(token.removeprefix("token-"))
