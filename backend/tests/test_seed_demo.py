import pytest
from sqlmodel import Session, func, select

from app.domain.enums import Role
from app.infrastructure.db.models import Event, User
from app.infrastructure.security.password_hasher import Argon2PasswordHasher
from scripts import seed_demo
from scripts.seed_demo import ATTENDEE_EMAILS, main


@pytest.fixture
def demo_env(session: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setattr(seed_demo, "get_engine", lambda: session.get_bind())
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    return session


def _count(session: Session, model: type) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


def test_loads_demo_data_and_is_idempotent(demo_env: Session) -> None:
    from app.application.admin_seed import ensure_admin
    from app.infrastructure.db.unit_of_work import SqlUnitOfWork
    from app.infrastructure.db.user_repository import SqlUserRepository

    ensure_admin(
        SqlUserRepository(demo_env),
        Argon2PasswordHasher(),
        SqlUnitOfWork(demo_env),
        "admin@example.com",
        "supersecret",
        "Site Admin",
    )
    assert main() == 0
    demo_env.expire_all()
    events, users = _count(demo_env, Event), _count(demo_env, User)
    assert events > 0
    assert users == 1 + len(ATTENDEE_EMAILS)
    roles = {u.email: u.role for u in demo_env.exec(select(User)).all()}
    assert roles["admin@example.com"] is Role.ADMIN
    assert all(roles[email] is Role.ATTENDEE for email in ATTENDEE_EMAILS)
    assert all(u.full_name.strip() for u in demo_env.exec(select(User)).all())

    assert main() == 0
    demo_env.expire_all()
    assert _count(demo_env, Event) == events
    assert _count(demo_env, User) == users


def test_fails_with_clear_message_when_admin_is_missing(
    demo_env: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main() == 1
    assert "Admin not found" in capsys.readouterr().err
    assert _count(demo_env, Event) == 0
