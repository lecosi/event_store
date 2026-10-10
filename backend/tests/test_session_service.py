from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import (
    EventNotFoundError,
    PermissionDeniedError,
    SessionNotFoundError,
)
from app.application.session_service import SessionService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventStateError
from app.domain.session import SessionConflictError, SessionDetails, SessionValidationError
from app.domain.speaker import Speaker
from app.domain.user import UserAccount
from tests.fakes import FakeEventRepository, FakeSessionRepository, FakeSpeakerRepository

BASE = datetime(2030, 1, 1, 9, tzinfo=UTC)

OWNER = UserAccount(id=1, email="o@x.com", password_hash="h", role=Role.ORGANIZER)
OTHER = UserAccount(id=2, email="p@x.com", password_hash="h", role=Role.ORGANIZER)
ADMIN = UserAccount(id=3, email="a@x.com", password_hash="h", role=Role.ADMIN)
ATTENDEE = UserAccount(id=4, email="t@x.com", password_hash="h", role=Role.ATTENDEE)


def at(hour: int) -> datetime:
    return BASE + timedelta(hours=hour)


def details(**overrides: object) -> SessionDetails:
    base: dict[str, object] = {
        "title": "Keynote",
        "speaker_id": 1,
        "start_at": at(1),
        "end_at": at(2),
        "capacity": 10,
    }
    base.update(overrides)
    return SessionDetails(**base)  # type: ignore[arg-type]


class Env:
    def __init__(self) -> None:
        self.events = FakeEventRepository()
        self.sessions = FakeSessionRepository()
        self.speakers = FakeSpeakerRepository(self.sessions)
        self.service = SessionService(self.events, self.sessions, self.speakers)
        self.event = self.add_event()
        self.speaker = self.speakers.add(Speaker(name="Ada", bio="", email=None))

    def add_event(self, **overrides: object) -> Event:
        fields: dict[str, object] = {
            "name": "Conf",
            "description": "",
            "location": "Lima",
            "start_at": at(0),
            "end_at": at(8),
            "capacity": 20,
            "organizer_id": OWNER.id,
        }
        fields.update(overrides)
        return self.events.add(Event(**fields))  # type: ignore[arg-type]

    def create(self, actor: UserAccount = OWNER, **overrides: object):  # noqa: ANN201
        assert self.event.id is not None
        return self.service.create(actor, self.event.id, details(**overrides))


@pytest.fixture
def env() -> Env:
    return Env()


def test_owner_creates_session(env: Env) -> None:
    created = env.create()
    assert created.id is not None
    assert created.event_id == env.event.id


def test_admin_can_create_but_non_owner_and_attendee_cannot(env: Env) -> None:
    env.create(ADMIN)
    with pytest.raises(PermissionDeniedError):
        env.create(OTHER, start_at=at(3), end_at=at(4))
    with pytest.raises(PermissionDeniedError):
        env.create(ATTENDEE, start_at=at(3), end_at=at(4))


def test_unknown_event_is_not_found(env: Env) -> None:
    with pytest.raises(EventNotFoundError):
        env.service.create(OWNER, 999, details())


@pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.FINISHED])
def test_closed_events_reject_session_changes(env: Env, status: EventStatus) -> None:
    created = env.create()
    env.event.status = status
    with pytest.raises(EventStateError):
        env.create(start_at=at(3), end_at=at(4))
    with pytest.raises(EventStateError):
        env.service.update(OWNER, env.event.id, created.id, details())
    with pytest.raises(EventStateError):
        env.service.delete(OWNER, env.event.id, created.id)


def test_unknown_speaker_is_rejected(env: Env) -> None:
    with pytest.raises(SessionValidationError):
        env.create(speaker_id=999)


def test_time_bounds_are_enforced(env: Env) -> None:
    with pytest.raises(SessionValidationError):
        env.create(start_at=at(2), end_at=at(2))
    with pytest.raises(SessionValidationError):
        env.create(start_at=at(-1), end_at=at(1))
    with pytest.raises(SessionValidationError):
        env.create(start_at=at(7), end_at=at(9))


def test_capacity_cannot_exceed_event_capacity(env: Env) -> None:
    env.create(capacity=20)
    with pytest.raises(SessionValidationError):
        env.create(capacity=21, start_at=at(3), end_at=at(4))
    with pytest.raises(SessionValidationError):
        env.create(capacity=0, start_at=at(3), end_at=at(4))


def test_same_speaker_cannot_overlap_even_across_events(env: Env) -> None:
    env.create(start_at=at(1), end_at=at(3))
    other_event = env.add_event()
    with pytest.raises(SessionConflictError):
        env.service.create(OWNER, other_event.id, details(start_at=at(2), end_at=at(4)))


def test_adjacent_sessions_of_same_speaker_are_allowed(env: Env) -> None:
    env.create(start_at=at(1), end_at=at(2))
    env.create(start_at=at(2), end_at=at(3))


def test_different_speakers_may_overlap(env: Env) -> None:
    second = env.speakers.add(Speaker(name="Bob", bio="", email=None))
    env.create()
    env.create(speaker_id=second.id)


def test_update_excludes_the_session_itself(env: Env) -> None:
    created = env.create(start_at=at(1), end_at=at(3))
    updated = env.service.update(
        OWNER, env.event.id, created.id, details(start_at=at(2), end_at=at(3), title="New")
    )
    assert updated.title == "New"
    assert updated.start_at == at(2)


def test_update_still_detects_overlap_with_other_sessions(env: Env) -> None:
    env.create(start_at=at(1), end_at=at(2))
    second = env.create(start_at=at(3), end_at=at(4))
    with pytest.raises(SessionConflictError):
        env.service.update(OWNER, env.event.id, second.id, details(start_at=at(1), end_at=at(2)))


def test_update_unknown_or_foreign_session_is_not_found(env: Env) -> None:
    other_event = env.add_event()
    created = env.create()
    with pytest.raises(SessionNotFoundError):
        env.service.update(OWNER, env.event.id, 999, details())
    with pytest.raises(SessionNotFoundError):
        env.service.update(OWNER, other_event.id, created.id, details())


def test_delete_removes_session(env: Env) -> None:
    created = env.create()
    env.service.delete(OWNER, env.event.id, created.id)
    assert env.service.list_for_event(env.event.id) == []
    with pytest.raises(SessionNotFoundError):
        env.service.delete(OWNER, env.event.id, created.id)


def test_list_is_ordered_by_start_and_includes_speaker_name(env: Env) -> None:
    env.create(start_at=at(5), end_at=at(6), title="Late")
    env.create(start_at=at(1), end_at=at(2), title="Early")
    listed = env.service.list_for_event(env.event.id)
    assert [s.session.title for s in listed] == ["Early", "Late"]
    assert listed[0].speaker_name == "Ada"
    assert listed[0].session.speaker_id == env.speaker.id
