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
from app.domain.user import InvalidFullNameError, UserAccount, WeakPasswordError
from tests.fakes import FakePasswordHasher, FakeTokenService, FakeUnitOfWork, FakeUserRepository

ADMIN_ACTOR = UserAccount(
    email="root@example.com", full_name="Test User", password_hash="h", role=Role.ADMIN, id=100
)


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
    user = service.register("  Ana@Example.com ", "supersecret", "Ana Perez")
    assert user.email == "ana@example.com"
    assert user.role is Role.ORGANIZER
    assert user.password_hash != "supersecret"


def test_register_honours_explicit_role(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez", role=Role.ATTENDEE)
    assert user.role is Role.ATTENDEE


def test_register_duplicate_email_fails(service: AuthService) -> None:
    service.register("ana@example.com", "supersecret", "Ana Perez")
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("ANA@example.com", "anothersecret", "Ana Perez")


def test_register_weak_password_fails(service: AuthService) -> None:
    with pytest.raises(WeakPasswordError):
        service.register("ana@example.com", "short", "Ana Perez")


def test_login_returns_token(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    assert service.login("ana@example.com", "supersecret") == f"token-{user.id}"


def test_login_wrong_password_and_unknown_email_raise_same_error(service: AuthService) -> None:
    service.register("ana@example.com", "supersecret", "Ana Perez")
    with pytest.raises(InvalidCredentialsError):
        service.login("ana@example.com", "wrongpassword")
    with pytest.raises(InvalidCredentialsError):
        service.login("nobody@example.com", "supersecret")


def test_login_inactive_user_fails(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    user.is_active = False
    with pytest.raises(InvalidCredentialsError):
        service.login("ana@example.com", "supersecret")


def test_authenticate_resolves_user_and_rejects_bad_tokens(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    assert service.authenticate(f"token-{user.id}").email == "ana@example.com"
    with pytest.raises(InvalidTokenError):
        service.authenticate("garbage")
    with pytest.raises(InvalidTokenError):
        service.authenticate("token-999")


def test_authenticate_rejects_inactive_user(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    user.is_active = False
    with pytest.raises(InvalidTokenError):
        service.authenticate(f"token-{user.id}")


def test_admin_updates_role_and_active_flag(service: AuthService, repo: FakeUserRepository) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    admin = UserAdminService(repo, FakeUnitOfWork())
    updated = admin.update_user(ADMIN_ACTOR, user.id, role=Role.ORGANIZER, is_active=False)
    assert updated.role is Role.ORGANIZER
    assert updated.is_active is False
    assert [u.email for u in admin.list_users().items] == ["ana@example.com"]


def test_admin_update_unknown_user_fails(repo: FakeUserRepository) -> None:
    with pytest.raises(UserNotFoundError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(ADMIN_ACTOR, 42, role=Role.ADMIN)


def _admin_in_repo(service: AuthService, repo: FakeUserRepository, email: str) -> UserAccount:
    user = service.register(email, "supersecret", "Ana Perez")
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
        service.register(f"u{i}@example.com", "supersecret", "Ana Perez")
    page = UserAdminService(repo, FakeUnitOfWork()).list_users(page=2, size=2)
    assert [u.email for u in page.items] == ["u2@example.com", "u3@example.com"]
    assert (page.total, page.page, page.size, page.pages) == (5, 2, 2, 3)
    assert UserAdminService(repo, FakeUnitOfWork()).list_users(page=9, size=2).items == []


def test_register_commits_once(service: AuthService, uow: FakeUnitOfWork) -> None:
    service.register("ana@example.com", "supersecret", "Ana Perez")
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_register_duplicate_email_does_not_commit_again_and_keeps_one_user(
    service: AuthService, repo: FakeUserRepository, uow: FakeUnitOfWork
) -> None:
    service.register("ana@example.com", "supersecret", "Ana Perez")
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("ana@example.com", "anothersecret", "Ana Perez")
    assert (uow.commits, uow.rollbacks) == (1, 1)
    assert len(repo.list_all()) == 1


def test_register_weak_password_never_commits(service: AuthService, uow: FakeUnitOfWork) -> None:
    with pytest.raises(WeakPasswordError):
        service.register("ana@example.com", "short", "Ana Perez")
    assert uow.commits == 0


def test_login_and_authenticate_never_commit(service: AuthService, uow: FakeUnitOfWork) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    service.authenticate(service.login("ana@example.com", "supersecret"))
    assert user.id is not None
    assert uow.commits == 1


def test_update_user_reads_then_saves_and_commits_once(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = service.register("ana@example.com", "supersecret", "Ana Perez")
    uow = FakeUnitOfWork()
    UserAdminService(repo, uow).update_user(ADMIN_ACTOR, user.id, role=Role.ORGANIZER)
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_failed_update_user_commits_nothing(repo: FakeUserRepository) -> None:
    uow = FakeUnitOfWork()
    with pytest.raises(UserNotFoundError):
        UserAdminService(repo, uow).update_user(ADMIN_ACTOR, 42, role=Role.ADMIN)
    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_register_stores_trimmed_full_name(service: AuthService) -> None:
    user = service.register("ana@example.com", "supersecret", "  Ana Perez  ")
    assert user.full_name == "Ana Perez"


@pytest.mark.parametrize("full_name", ["", "   ", "x" * 201])
def test_register_rejects_invalid_full_name(service: AuthService, full_name: str) -> None:
    with pytest.raises(InvalidFullNameError):
        service.register("ana@example.com", "supersecret", full_name)


def _registered(service: AuthService, email: str, full_name: str = "Ana Perez") -> UserAccount:
    return service.register(email, "supersecret", full_name)


def test_admin_changes_only_the_full_name(service: AuthService, repo: FakeUserRepository) -> None:
    user = _registered(service, "ana@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR, user.id, full_name="  Ana Maria Perez  "
    )
    assert updated.full_name == "Ana Maria Perez"
    assert (updated.email, updated.role, updated.is_active) == (
        "ana@example.com",
        Role.ORGANIZER,
        True,
    )


def test_admin_changes_only_the_email(service: AuthService, repo: FakeUserRepository) -> None:
    user = _registered(service, "ana@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR, user.id, email="ana.perez@example.com"
    )
    assert updated.email == "ana.perez@example.com"
    assert updated.full_name == "Ana Perez"


def test_admin_changes_name_email_role_and_active_flag_together(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR,
        user.id,
        full_name="Ana M. Perez",
        email="ana.m@example.com",
        role=Role.ATTENDEE,
        is_active=False,
    )
    assert (updated.full_name, updated.email, updated.role, updated.is_active) == (
        "Ana M. Perez",
        "ana.m@example.com",
        Role.ATTENDEE,
        False,
    )


def test_admin_email_is_normalized_like_registration(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR, user.id, email="  Ana.Perez@Example.COM "
    )
    assert updated.email == "ana.perez@example.com"
    assert service.login("ana.perez@example.com", "supersecret")


def test_admin_cannot_take_an_email_used_by_another_user(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    _registered(service, "bob@example.com")
    with pytest.raises(EmailAlreadyRegisteredError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(
            ADMIN_ACTOR, user.id, email="  BOB@example.com"
        )
    assert repo.get_by_id(user.id).email == "ana@example.com"


def test_admin_resending_the_current_email_is_not_a_conflict(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR, user.id, email="ANA@example.com", full_name="Ana Maria"
    )
    assert (updated.email, updated.full_name) == ("ana@example.com", "Ana Maria")


@pytest.mark.parametrize("full_name", ["", "   ", "x" * 201])
def test_admin_rejects_invalid_full_name_without_committing(
    service: AuthService, repo: FakeUserRepository, full_name: str
) -> None:
    user = _registered(service, "ana@example.com")
    uow = FakeUnitOfWork()
    with pytest.raises(InvalidFullNameError):
        UserAdminService(repo, uow).update_user(ADMIN_ACTOR, user.id, full_name=full_name)
    assert uow.commits == 0
    assert repo.get_by_id(user.id).full_name == "Ana Perez"


def test_admin_email_conflict_rolls_back_without_committing(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    _registered(service, "bob@example.com")
    uow = FakeUnitOfWork()
    with pytest.raises(EmailAlreadyRegisteredError):
        UserAdminService(repo, uow).update_user(ADMIN_ACTOR, user.id, email="bob@example.com")
    assert (uow.commits, uow.rollbacks) == (0, 1)


def test_admin_edits_own_name_and_email(service: AuthService, repo: FakeUserRepository) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    updated = UserAdminService(repo, FakeUnitOfWork()).update_user(
        me, me.id, full_name="Root Admin", email="boss@example.com"
    )
    assert (updated.full_name, updated.email, updated.role) == (
        "Root Admin",
        "boss@example.com",
        Role.ADMIN,
    )


def test_admin_self_lockout_still_applies_when_editing_name(
    service: AuthService, repo: FakeUserRepository
) -> None:
    me = _admin_in_repo(service, repo, "root@example.com")
    with pytest.raises(SelfLockoutError):
        UserAdminService(repo, FakeUnitOfWork()).update_user(
            me, me.id, full_name="Root Admin", is_active=False
        )
    assert repo.get_by_id(me.id).full_name == "Ana Perez"


def test_token_issued_before_an_email_change_still_authenticates(
    service: AuthService, repo: FakeUserRepository
) -> None:
    user = _registered(service, "ana@example.com")
    token = service.login("ana@example.com", "supersecret")
    UserAdminService(repo, FakeUnitOfWork()).update_user(
        ADMIN_ACTOR, user.id, email="ana.new@example.com"
    )
    assert service.authenticate(token).email == "ana.new@example.com"
