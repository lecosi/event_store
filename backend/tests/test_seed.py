import pytest

from app.application.admin_seed import ensure_admin
from app.domain.enums import Role
from app.infrastructure.security.password_hasher import Argon2PasswordHasher
from tests.fakes import FakeUnitOfWork, FakeUserRepository


def test_creates_admin_with_hashed_password() -> None:
    users, hasher = FakeUserRepository(), Argon2PasswordHasher()
    admin = ensure_admin(users, hasher, FakeUnitOfWork(), "  Admin@Example.com ", "supersecret")
    assert admin.email == "admin@example.com"
    assert admin.role is Role.ADMIN
    assert admin.password_hash != "supersecret"
    assert hasher.verify("supersecret", admin.password_hash)


def test_is_idempotent_and_promotes_existing_user() -> None:
    users, hasher = FakeUserRepository(), Argon2PasswordHasher()
    users.add("admin@example.com", hasher.hash("supersecret"), Role.ATTENDEE)
    uow = FakeUnitOfWork()
    admin = ensure_admin(users, hasher, uow, "admin@example.com", "supersecret")
    assert admin.role is Role.ADMIN
    again = ensure_admin(users, hasher, uow, "admin@example.com", "supersecret")
    assert again.id == admin.id
    assert len(users.list_all()) == 1


def test_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        ensure_admin(
            FakeUserRepository(), Argon2PasswordHasher(), FakeUnitOfWork(), "a@example.com", "123"
        )


def test_script_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.seed import main

    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert main() == 1


def test_creating_admin_commits_once() -> None:
    uow = FakeUnitOfWork()
    ensure_admin(FakeUserRepository(), Argon2PasswordHasher(), uow, "a@example.com", "supersecret")
    assert uow.commits == 1


def test_existing_admin_is_left_untouched_without_commit() -> None:
    users, hasher, uow = FakeUserRepository(), Argon2PasswordHasher(), FakeUnitOfWork()
    users.add("a@example.com", hasher.hash("supersecret"), Role.ADMIN)
    ensure_admin(users, hasher, uow, "a@example.com", "supersecret")
    assert uow.commits == 0


def test_weak_password_commits_nothing() -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(ValueError):
        ensure_admin(FakeUserRepository(), Argon2PasswordHasher(), uow, "a@example.com", "123")
    assert uow.commits == 0
