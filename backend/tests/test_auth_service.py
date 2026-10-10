import pytest

from app.application.auth_service import AuthService
from app.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.domain.enums import Role
from app.domain.user import WeakPasswordError
from tests.fakes import FakePasswordHasher, FakeTokenService, FakeUserRepository


@pytest.fixture
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def service(repo: FakeUserRepository) -> AuthService:
    return AuthService(repo, FakePasswordHasher(), FakeTokenService())


def test_register_creates_organizer_with_hashed_password(service: AuthService) -> None:
    user = service.register("  Ana@Example.com ", "supersecret")
    assert user.email == "ana@example.com"
    assert user.role is Role.ORGANIZER
    assert user.password_hash != "supersecret"


def test_register_honours_explicit_role(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", role=Role.ATTENDEE)
    assert user.role is Role.ATTENDEE


def test_register_duplicate_email_fails(service: AuthService) -> None:
    service.register("ana@example.com", "supersecret")
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("ANA@example.com", "anothersecret")


def test_register_weak_password_fails(service: AuthService) -> None:
    with pytest.raises(WeakPasswordError):
        service.register("ana@example.com", "short")


def test_login_returns_token(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret")
    assert service.login("ana@example.com", "supersecret") == f"token-{user.id}"


def test_login_wrong_password_and_unknown_email_raise_same_error(service: AuthService) -> None:
    service.register("ana@example.com", "supersecret")
    with pytest.raises(InvalidCredentialsError):
        service.login("ana@example.com", "wrongpassword")
    with pytest.raises(InvalidCredentialsError):
        service.login("nobody@example.com", "supersecret")


def test_login_inactive_user_fails(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret")
    user.is_active = False
    with pytest.raises(InvalidCredentialsError):
        service.login("ana@example.com", "supersecret")


def test_authenticate_resolves_user_and_rejects_bad_tokens(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret")
    assert service.authenticate(f"token-{user.id}").email == "ana@example.com"
    with pytest.raises(InvalidTokenError):
        service.authenticate("garbage")
    with pytest.raises(InvalidTokenError):
        service.authenticate("token-999")


def test_authenticate_rejects_inactive_user(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret")
    user.is_active = False
    with pytest.raises(InvalidTokenError):
        service.authenticate(f"token-{user.id}")
