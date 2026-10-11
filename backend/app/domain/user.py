"""User aggregate and password policy (pure domain, no framework imports)."""

from dataclasses import dataclass
from math import ceil

from app.domain.enums import Role

MIN_PASSWORD_LENGTH = 8
MAX_FULL_NAME_LENGTH = 200


class WeakPasswordError(ValueError):
    """Raised when a password does not satisfy the password policy."""


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")


class InvalidFullNameError(ValueError):
    """Raised when a full name is blank or longer than the allowed length."""


def normalize_full_name(full_name: str) -> str:
    """Return the trimmed full name, or raise InvalidFullNameError if it is not valid."""
    trimmed = full_name.strip()
    if not trimmed:
        raise InvalidFullNameError("Full name must not be blank")
    if len(trimmed) > MAX_FULL_NAME_LENGTH:
        raise InvalidFullNameError(
            f"Full name must be at most {MAX_FULL_NAME_LENGTH} characters long"
        )
    return trimmed


@dataclass
class UserAccount:
    email: str
    full_name: str
    password_hash: str
    role: Role = Role.ATTENDEE
    is_active: bool = True
    id: int | None = None


@dataclass(frozen=True)
class UserPage:
    items: list[UserAccount]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size) if self.total else 0
