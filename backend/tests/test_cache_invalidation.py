from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import (
    EventNotFoundError,
    PermissionDeniedError,
    SpeakerEmailTakenError,
    SpeakerInUseError,
)
from app.application.event_service import EventService
from app.application.ports import EVENTS_NAMESPACE, SESSIONS_NAMESPACE, SPEAKERS_NAMESPACE
from app.application.session_service import SessionService
from app.application.speaker_service import SpeakerService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventDetails, EventValidationError
from app.domain.session import Session, SessionDetails
from app.domain.speaker import Speaker, SpeakerDetails
from app.domain.user import UserAccount
from tests.fakes import (
    FakeCache,
    FakeEventRepository,
    FakeSessionRepository,
    FakeSpeakerRepository,
    FakeUnitOfWork,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)
OWNER = UserAccount(
    id=1, email="o@x.com", full_name="Test User", password_hash="h", role=Role.ORGANIZER
)
ATTENDEE = UserAccount(
    id=4, email="t@x.com", full_name="Test User", password_hash="h", role=Role.ATTENDEE
)


class CommitAwareCache(FakeCache):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow
        self.commits_seen_at_invalidation: list[int] = []

    def invalidate(self, namespace: str) -> None:
        self.commits_seen_at_invalidation.append(self._uow.commits)
        super().invalidate(namespace)


class Env:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.cache = CommitAwareCache(self.uow)
        self.events = FakeEventRepository()
        self.sessions = FakeSessionRepository()
        self.speakers = FakeSpeakerRepository(self.sessions)
        self.event_service = EventService(
            self.events, self.uow, clock=lambda: NOW, cache=self.cache
        )
        self.session_service = SessionService(
            self.events, self.sessions, self.speakers, self.uow, self.cache
        )
        self.speaker_service = SpeakerService(self.speakers, self.uow, self.cache)
        self.event = self.events.add(
            Event(
                name="Conf",
                description="",
                location="Lima",
                start_at=NOW + timedelta(hours=1),
                end_at=NOW + timedelta(hours=9),
                capacity=20,
                organizer_id=OWNER.id,
            )
        )
        self.speaker = self.speakers.add(Speaker(name="Ada", bio="", email="ada@x.com"))
        self.session = self.sessions.add(
            Session(
                event_id=self.event.id,
                speaker_id=self.speaker.id,
                title="Keynote",
                start_at=NOW + timedelta(hours=2),
                end_at=NOW + timedelta(hours=3),
                capacity=10,
            )
        )
        self.unused_speaker = self.speakers.add(Speaker(name="Grace", bio="", email=None))

    @property
    def invalidated(self) -> list[str]:
        return self.cache.invalidations


def event_details(**overrides: object) -> EventDetails:
    base: dict[str, object] = {
        "name": "PyCon",
        "description": "",
        "location": "Lima",
        "start_at": NOW + timedelta(days=1),
        "end_at": NOW + timedelta(days=2),
        "capacity": 10,
    }
    base.update(overrides)
    return EventDetails(**base)  # type: ignore[arg-type]


def session_details(**overrides: object) -> SessionDetails:
    base: dict[str, object] = {
        "title": "Talk",
        "speaker_id": 1,
        "start_at": NOW + timedelta(hours=4),
        "end_at": NOW + timedelta(hours=5),
        "capacity": 10,
    }
    base.update(overrides)
    return SessionDetails(**base)  # type: ignore[arg-type]


def speaker_details(**overrides: object) -> SpeakerDetails:
    base: dict[str, object] = {"name": "Linus", "bio": "", "email": "linus@x.com"}
    base.update(overrides)
    return SpeakerDetails(**base)  # type: ignore[arg-type]


@pytest.fixture
def env() -> Env:
    return Env()


def test_event_create_invalidates_events_only(env: Env) -> None:
    env.event_service.create(OWNER, event_details())
    assert env.invalidated == [EVENTS_NAMESPACE]


def test_event_update_invalidates_events_only(env: Env) -> None:
    env.event_service.update(OWNER, env.event.id, event_details(start_at=NOW + timedelta(hours=1)))
    assert env.invalidated == [EVENTS_NAMESPACE]


def test_event_status_change_invalidates_events_only(env: Env) -> None:
    env.event_service.change_status(OWNER, env.event.id, EventStatus.PUBLISHED)
    assert env.invalidated == [EVENTS_NAMESPACE]


def test_event_delete_invalidates_events_and_sessions(env: Env) -> None:
    env.event_service.delete(OWNER, env.event.id)
    assert sorted(env.invalidated) == sorted([EVENTS_NAMESPACE, SESSIONS_NAMESPACE])


def test_session_create_invalidates_sessions_only(env: Env) -> None:
    env.session_service.create(
        OWNER, env.event.id, session_details(speaker_id=env.unused_speaker.id)
    )
    assert env.invalidated == [SESSIONS_NAMESPACE]


def test_session_update_invalidates_sessions_only(env: Env) -> None:
    env.session_service.update(
        OWNER, env.event.id, env.session.id, session_details(speaker_id=env.speaker.id)
    )
    assert env.invalidated == [SESSIONS_NAMESPACE]


def test_session_delete_invalidates_sessions_only(env: Env) -> None:
    env.session_service.delete(OWNER, env.event.id, env.session.id)
    assert env.invalidated == [SESSIONS_NAMESPACE]


def test_speaker_create_invalidates_speakers_only(env: Env) -> None:
    env.speaker_service.create(OWNER, speaker_details())
    assert env.invalidated == [SPEAKERS_NAMESPACE]


def test_speaker_update_invalidates_speakers_and_sessions(env: Env) -> None:
    env.speaker_service.update(OWNER, env.speaker.id, speaker_details(email="ada@x.com"))
    assert sorted(env.invalidated) == sorted([SPEAKERS_NAMESPACE, SESSIONS_NAMESPACE])


def test_speaker_delete_invalidates_speakers_and_sessions(env: Env) -> None:
    env.speaker_service.delete(OWNER, env.unused_speaker.id)
    assert sorted(env.invalidated) == sorted([SPEAKERS_NAMESPACE, SESSIONS_NAMESPACE])


def test_invalidation_happens_after_the_transaction_commits(env: Env) -> None:
    env.event_service.create(OWNER, event_details())
    env.speaker_service.delete(OWNER, env.unused_speaker.id)
    env.session_service.delete(OWNER, env.event.id, env.session.id)
    assert env.cache.commits_seen_at_invalidation == [1, 2, 2, 3]


def test_cached_entries_of_an_invalidated_namespace_are_dropped(env: Env) -> None:
    env.cache.set(EVENTS_NAMESPACE, "page=1", "stale", ttl_seconds=60)
    env.cache.set(SPEAKERS_NAMESPACE, "page=1", "kept", ttl_seconds=60)
    env.event_service.create(OWNER, event_details())
    assert env.cache.get(EVENTS_NAMESPACE, "page=1") is None
    assert env.cache.get(SPEAKERS_NAMESPACE, "page=1") == "kept"


@pytest.mark.parametrize(
    "write",
    [
        lambda e: e.event_service.create(ATTENDEE, event_details()),
        lambda e: e.event_service.create(OWNER, event_details(capacity=0)),
        lambda e: e.event_service.update(ATTENDEE, e.event.id, event_details()),
        lambda e: e.event_service.change_status(OWNER, 999, EventStatus.PUBLISHED),
        lambda e: e.event_service.delete(ATTENDEE, e.event.id),
        lambda e: e.session_service.create(ATTENDEE, e.event.id, session_details()),
        lambda e: e.session_service.update(OWNER, 999, e.session.id, session_details()),
        lambda e: e.session_service.delete(ATTENDEE, e.event.id, e.session.id),
        lambda e: e.speaker_service.create(ATTENDEE, speaker_details()),
        lambda e: e.speaker_service.create(OWNER, speaker_details(email="ada@x.com")),
        lambda e: e.speaker_service.update(ATTENDEE, e.speaker.id, speaker_details()),
        lambda e: e.speaker_service.delete(OWNER, e.speaker.id),
    ],
    ids=[
        "event-create-forbidden",
        "event-create-invalid",
        "event-update-forbidden",
        "event-status-missing-event",
        "event-delete-forbidden",
        "session-create-forbidden",
        "session-update-missing-event",
        "session-delete-forbidden",
        "speaker-create-forbidden",
        "speaker-create-duplicate-email",
        "speaker-update-forbidden",
        "speaker-delete-in-use",
    ],
)
def test_failed_writes_invalidate_nothing(env: Env, write) -> None:
    with pytest.raises(
        (
            PermissionDeniedError,
            EventValidationError,
            EventNotFoundError,
            SpeakerEmailTakenError,
            SpeakerInUseError,
        )
    ):
        write(env)
    assert env.invalidated == []
    assert env.uow.commits == 0
    assert env.uow.rollbacks == 1
