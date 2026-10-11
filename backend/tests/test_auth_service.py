import pytest

from app.application.auth_service import AuthService, UserAdminService
from app.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    SelfLockoutError,
    UserNotFoundError,
)
from app.domain.enums import Role
from app.domain.user import UserAccount, WeakPasswordError
from tests.fakes import FakePasswordHasher, FakeTokenService, FakeUnitOfWork, FakeUserRepository

ADMIN_ACTOR = UserAccount(email="root@example.com", password_hash="h", role=Role.ADMIN, id=100)


@pytest.fixture
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def service(repo: FakeUserRepository, uow: FakeUnitOfWork) -> AuthService:
    return AuthService(repo, FakePasswordHasher(), FakeTokenService(), uow)


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


def test_admin_updates_role_and_active_flag(service: AuthService, repo: FakeUserRepository) -> None:
    user = service.register("ana@example.com", "supersecret")
    admin = UserAdminService(repo, FakeUnitOfWork())
    updated = admin.update_user(ADMIN_ACTOR, user.id, role=Role.ORGANIZER, is_active=False)
    assert updated.role is Role.ORGANIZER
    assert updated.is_active is False
    assert [u.email for u in admin.list_users().items] == ["ana@example.com"]


def test_admin_update_unknown_user_fails(repo: FakeUserRepository) -> None:
    with pytest.raises(UserNotFoundError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(ADMIN_ACTOR, 42, role=Role.ADMIN)


def _admin_in_repo(service: AuthService, repo: FakeUserRepository, email: str) -> UserAccount:
    user = service.register(email, "supersecret")
    user.role = Role.ADMIN
    return repo.save(user)


def test_admin_cannot_demote_self(service: AuthService, repo: FakeUserRepository) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    with pytest.raises(SelfLockoutError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(me, me.id, role=Role.ORGANIZER)
    assert repo.get_by_id(me.id).role is Role.ADMIN


def test_admin_cannot_deactivate_self(service: AuthService, repo: FakeUserRepository) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    with pytest.raises(SelfLockoutError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(me, me.id, is_active=False)
    assert repo.get_by_id(me.id).is_active is True


def test_admin_self_noop_updates_succeed(service: AuthService, repo: FakeUserRepository) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        me, me.id, role=Role.ADMIN, is_active=True
    )
    assert (updated.role, updated.is_active) == (Role.ADMIN, True)


def test_admin_can_demote_and_deactivate_another_admin(
    service: AuthService, repo: FakeUserRepository
) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    other = _admin_in_repo(service, repo, "other@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        me, other.id, role=Role.ORGANIZER, is_active=False
    )
    assert (updated.role, updated.is_active) == (Role.ORGANIZER, False)


def test_list_users_pages_ordered_by_id(service: AuthService, repo: FakeUserRepository) -> None:
    for i in range(5):
        service.register(f"u{i}@example.com", "supersecret")
    page = UserAdminService(repo, FakeUnitOfWork()).list_users(page=2, size=2)
    assert [u.email for u in page.items] == ["u2@example.com", "u3@example.com"]
    assert (page.total, page.page, page.size, page.pages) == (5, 2, 2, 3)
    assert UserAdminService(repo, FakeUnitOfWork()).list_users(page=9, size=2).items == []


def test_register_commits_once(service: AuthService, uow: FakeUnitOfWork) -> None:
    service.register("ana@example.com", "supersecret")
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_register_duplicate_email_does_not_commit_again_and_keeps_one_user(
    service: AuthService, repo: FakeUserRepository, uow: FakeUnitOfWork
) -> None:
    service.register("ana@example.com", "supersecret")
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("ana@example.com", "anothersecret")
    assert (uow.commits, uow.rollbacks) == (1, 1)
    assert len(repo.list_all()) == 1


def test_register_weak_password_never_commits(service: AuthService, uow: FakeUnitOfWork) -> None:
    with pytest.raises(WeakPasswordError):
        service.register("ana@example.com", "short")
    assert uow.commits == 0


def test_login_and_authenticate_never_commit(service: AuthService, uow: FakeUnitOfWork) -> None:
    user = service.register("ana@example.com", "supersecret")
    service.authenticate(service.login("ana@example.com", "supersecret"))
    assert user.id is not None
    assert uow.commits == 1


def test_update_user_reads_then_saves_and_commits_once(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = service.register("ana@example.com", "supersecret")
    uow = FakeUnitOfWork()
    UserAdminService(repo, uow).update_user(ADMIN_ACTOR, user.id, role=Role.ORGANIZER)
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_failed_update_user_commits_nothing(repo: FakeUserRepository) -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(UserNotFoundError):
        UserAdminService(repo, uow).update_user(ADMIN_ACTOR, 42, role=Role.ADMIN)
    assert (uow.commits, uow.rollbacks) == (0, 1)
