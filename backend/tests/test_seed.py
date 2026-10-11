import pytest

from app.application.admin_seed import ensure_admin
from app.domain.enums import Role
from app.domain.user import InvalidFullNameError, UserAccount
from app.infrastructure.security.password_hasher import Argon2PasswordHasher
from tests.fakes import FakeUnitOfWork, FakeUserRepository


def test_creates_admin_with_hashed_password() -> None:
    users, hasher = FakeUserRepository(), Argon2PasswordHasher()
    admin = ensure_admin(
        users, hasher, FakeUnitOfWork(), "  Admin@Example.com ", "supersecret", "Site Admin"
    )
    assert admin.email == "admin@example.com"
    assert admin.role is Role.ADMIN
    assert admin.password_hash != "supersecret"
    assert hasher.verify("supersecret", admin.password_hash)


def test_is_idempotent_and_promotes_existing_user() -> None:
    users, hasher = FakeUserRepository(), Argon2PasswordHasher()
    users.add(
        UserAccount(
            email="admin@example.com",
            full_name="Test User",
            password_hash=hasher.hash("supersecret"),
            role=Role.ATTENDEE,
        )
    )
    uow = FakeUnitOfWork()
    admin = ensure_admin(users, hasher, uow, "admin@example.com", "supersecret", "Site Admin")
    assert admin.role is Role.ADMIN
    again = ensure_admin(users, hasher, uow, "admin@example.com", "supersecret", "Site Admin")
    assert again.id == admin.id
    assert len(users.list_all()) == 1


def test_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        ensure_admin(
            FakeUserRepository(),
            Argon2PasswordHasher(),
            FakeUnitOfWork(),
            "a@example.com",
            "123",
            "Site Admin",
        )


def test_script_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.seed import main

    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert main() == 1


def test_creating_admin_commits_once() -> None:
    uow = FakeUnitOfWork()
    ensure_admin(
        FakeUserRepository(),
        Argon2PasswordHasher(),
        uow,
        "a@example.com",
        "supersecret",
        "Site Admin",
    )
    assert uow.commits == 1


def test_existing_admin_is_left_untouched_without_commit() -> None:
    users, hasher, uow = FakeUserRepository(), Argon2PasswordHasher(), FakeUnitOfWork()
    users.add(
        UserAccount(
            email="a@example.com",
            full_name="Test User",
            password_hash=hasher.hash("supersecret"),
            role=Role.ADMIN,
        )
    )
    ensure_admin(users, hasher, uow, "a@example.com", "supersecret", "Site Admin")
    assert uow.commits == 0


def test_weak_password_commits_nothing() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(ValueError):
        ensure_admin(
            FakeUserRepository(), Argon2PasswordHasher(), uow, "a@example.com", "123", "Site Admin"
        )
    assert uow.commits == 0


def test_created_admin_gets_the_given_full_name() -> None:
    admin = ensure_admin(
        FakeUserRepository(),
        Argon2PasswordHasher(),
        FakeUnitOfWork(),
        "a@example.com",
        "supersecret",
        "  Site Admin ",
    )
    assert admin.full_name == "Site Admin"


def test_promoted_admin_keeps_its_own_full_name() -> None:
    users, hasher = FakeUserRepository(), Argon2PasswordHasher()
    users.add(
        UserAccount(
            email="a@example.com",
            full_name="Original Name",
            password_hash=hasher.hash("supersecret"),
            role=Role.ATTENDEE,
        )
    )
    admin = ensure_admin(users, hasher, FakeUnitOfWork(), "a@example.com", "supersecret", "Other")
    assert admin.full_name == "Original Name"


def test_rejects_blank_full_name() -> None:
    with pytest.raises(InvalidFullNameError):
        ensure_admin(
            FakeUserRepository(),
            Argon2PasswordHasher(),
            FakeUnitOfWork(),
            "a@example.com",
            "supersecret",
            "   ",
        )
