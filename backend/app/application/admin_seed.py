"""Use case that guarantees an administrator account exists (idempotent)."""

from app.application.auth_service import normalize_email
from app.application.ports import PasswordHasher, UnitOfWork, UserRepository, transaction
from app.domain.enums import Role
from app.domain.user import UserAccount, validate_password


def ensure_admin(
    users: UserRepository, hasher: PasswordHasher, uow: UnitOfWork, email: str, password: str
) -> UserAccount:
    """Create the admin, or promote the existing account with that email."""
    validate_password(password)
    email = normalize_email(email)
    existing = users.get_by_email(email)
    if existing is None:
        with transaction(uow):
            account = UserAccount(email=email, password_hash=hasher.hash(password), role=Role.ADMIN)
            return users.add(account)
    if existing.role is not Role.ADMIN:
        existing.role = Role.ADMIN
        with transaction(uow):
            return users.save(existing)
    return existing
