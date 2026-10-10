"""User aggregate and password policy (pure domain, no framework imports)."""

from dataclasses import dataclass

from app.domain.enums import Role

MIN_PASSWORD_LENGTH = 8


class WeakPasswordError(ValueError):
    """Raised when a password does not satisfy the password policy."""


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")


@dataclass
class UserAccount:
    email: str
    password_hash: str
    role: Role = Role.ATTENDEE
    is_active: bool = True
    id: int | None = None
