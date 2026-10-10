"""Ports (abstractions) that the application layer depends on.

Infrastructure provides the implementations; use cases receive them by injection.
Each port is small and focused (interface segregation).
"""

from typing import Protocol

from app.domain.enums import Role
from app.domain.user import UserAccount


class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> UserAccount | None: ...

    def get_by_email(self, email: str) -> UserAccount | None: ...

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        """Persist a new user; raise EmailAlreadyRegisteredError on duplicate email."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: int) -> str: ...

    def read_subject(self, token: str) -> int:
        """Return the user id carried by the token; raise InvalidTokenError otherwise."""
        ...
