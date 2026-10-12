from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.domain.enums import EventStatus, Role
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.models import Event, Registration, User
from scripts import close_past_events
from scripts.close_past_events import main

NOW = datetime.now(UTC)


@pytest.fixture
def script_env(session: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    monkeypatch.setattr(close_past_events, "get_engine", lambda: session.get_bind())
    return session


def add_event(session: Session, owner: User, status: EventStatus, ends_in: timedelta) -> Event:
    assert owner.id is not None
    event = Event(
        name="PyCon",
        description="",
        location="Lima",
        start_at=NOW + ends_in - timedelta(hours=5),
        end_at=NOW + ends_in,
        capacity=10,
        status=status,
        organizer_id=owner.id,
    )
    session.add(event)
    session.commit()
    return event


def organizer(session: Session) -> User:
    user = User(email="org@example.com", full_name="Org", password_hash="h", role=Role.ORGANIZER)
    session.add(user)
    session.commit()
    return user


def status_of(session: Session, event: Event) -> EventStatus:
    session.expire_all()
    stored = session.get(Event, event.id)
    assert stored is not None
    return stored.status


def test_script_finishes_only_published_events_that_already_ended(
    script_env: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = organizer(script_env)
    past = add_event(script_env, owner, EventStatus.PUBLISHED, timedelta(days=-1))
    running = add_event(script_env, owner, EventStatus.PUBLISHED, timedelta(hours=1))
    draft = add_event(script_env, owner, EventStatus.DRAFT, timedelta(days=-1))
    cancelled = add_event(script_env, owner, EventStatus.CANCELLED, timedelta(days=-1))

    assert main() == 0

    assert status_of(script_env, past) is EventStatus.FINISHED
    assert status_of(script_env, running) is EventStatus.PUBLISHED
    assert status_of(script_env, draft) is EventStatus.DRAFT
    assert status_of(script_env, cancelled) is EventStatus.CANCELLED
    assert capsys.readouterr().out.strip() == "Finished events: 1"


def test_script_is_idempotent(script_env: Session, capsys: pytest.CaptureFixture[str]) -> None:
    add_event(script_env, organizer(script_env), EventStatus.PUBLISHED, timedelta(days=-1))

    main()
    capsys.readouterr()
    assert main() == 0

    assert capsys.readouterr().out.strip() == "Finished events: 0"


def test_script_keeps_the_registrations_of_finished_events(script_env: Session) -> None:
    owner = organizer(script_env)
    event = add_event(script_env, owner, EventStatus.PUBLISHED, timedelta(days=-1))
    assert owner.id is not None and event.id is not None
    script_env.add(Registration(user_id=owner.id, event_id=event.id))
    script_env.commit()

    main()

    script_env.expire_all()
    assert len(script_env.exec(select(Registration)).all()) == 1


def test_repository_lists_only_published_events_ended_before_the_moment(
    session: Session,
) -> None:
    owner = organizer(session)
    ended = add_event(session, owner, EventStatus.PUBLISHED, timedelta(days=-1))
    add_event(session, owner, EventStatus.PUBLISHED, timedelta(days=1))
    add_event(session, owner, EventStatus.FINISHED, timedelta(days=-1))

    found = SqlEventRepository(session).list_published_ended_before(NOW)

    assert [event.id for event in found] == [ended.id]
