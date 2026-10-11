"""Authentication and user-management use cases.

Depends only on the ports in ``app.application.ports``.
"""

from app.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    SelfLockoutError,
    UserNotFoundError,
)
from app.application.ports import (
    PasswordHasher,
    TokenService,
    UnitOfWork,
    UserRepository,
    transaction,
)
from app.domain.enums import Role
from app.domain.user import UserAccount, UserPage, normalize_full_name, validate_password


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(
        self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService, uow: UnitOfWork
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._uow = uow

    def register(
        self, email: str, password: str, full_name: str, role: Role = Role.ORGANIZER
    ) -> UserAccount:
        validate_password(password)
        full_name = normalize_full_name(full_name)
        email = normalize_email(email)
        with transaction(self._uow):
            if self._users.get_by_email(email) is not None:
                raise EmailAlreadyRegisteredError(email)
            account = UserAccount(
                email=email,
                full_name=full_name,
                password_hash=self._hasher.hash(password),
                role=role,
            )
            return self._users.add(account)

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


class UserAdminService:
    def __init__(self, users: UserRepository, uow: UnitOfWork) -> None:
        self._users = users
        self._uow = uow

    def list_users(self, page: int = 1, size: int = 10) -> UserPage:
        items, total = self._users.list_page(page, size)
        return UserPage(items=items, total=total, page=page, size=size)

    def update_user(
        self,
        actor: UserAccount,
        user_id: int,
        role: Role | None = None,
        is_active: bool | None = None,
    ) -> UserAccount:
        """Apply a partial update; an admin may not demote or deactivate themselves."""
        with transaction(self._uow):
            if actor.id == user_id and (
                (role is not None and role is not Role.ADMIN) or is_active is False
            ):
                raise SelfLockoutError(user_id)
            user = self._users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError(user_id)
            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active
            return self._users.save(user)
