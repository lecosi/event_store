"""Authentication use cases.

Depends only on the ports in ``app.application.ports``.
"""

from app.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.application.ports import PasswordHasher, TokenService, UserRepository
from app.domain.enums import Role
from app.domain.user import UserAccount, validate_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    def register(self, email: str, password: str, role: Role = Role.ORGANIZER) -> UserAccount:
        validate_password(password)
        email = normalize_email(email)
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)
        return self._users.add(email, self._hasher.hash(password), role)

    def login(self, email: str, password: str) -> str:
        user = self._users.get_by_email(normalize_email(email))
        if user is None:
            # Spend comparable time as a real check to limit user enumeration by timing.
            self._hasher.hash(password)
            raise InvalidCredentialsError
        if not self._hasher.verify(password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError
        assert user.id is not None
        return self._tokens.create_access_token(user.id)

    def authenticate(self, token: str) -> UserAccount:
        """Resolve a bearer token to an active user."""
        user_id = self._tokens.read_subject(token)
        user = self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError
        return user
