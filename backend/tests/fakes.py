from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime

import redis

from app.application.errors import (
    EmailAlreadyRegisteredError,
    EventNotFoundError,
    InvalidTokenError,
    SessionNotFoundError,
)
from app.application.ports import EnrollmentRule, RegistrationRule
from app.domain.enums import EventStatus
from app.domain.event import Event, EventFilters, ParticipantFilters, ensure_utc
from app.domain.registration import (
    AlreadyRegisteredError,
    ParticipantRow,
    RegisteredEvent,
    Registration,
)
from app.domain.session import Session
from app.domain.session_registration import (
    AlreadyEnrolledError,
    EnrollmentContext,
    SessionParticipantFilters,
    SessionParticipantRow,
    SessionRegistration,
)
from app.domain.speaker import Speaker
from app.domain.user import UserAccount


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, UserAccount] = {}

    def get_by_id(self, user_id: int) -> UserAccount | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> UserAccount | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def list_all(self) -> list[UserAccount]:
        return list(self._by_id.values())

    def list_page(self, page: int, size: int) -> tuple[list[UserAccount], int]:
        users = sorted(self._by_id.values(), key=lambda u: u.id or 0)
        start = (page - 1) * size
        return users[start : start + size], len(users)

    def add(self, user: UserAccount) -> UserAccount:
        if self.get_by_email(user.email):
            raise EmailAlreadyRegisteredError(user.email)
        stored = replace(user, id=len(self._by_id) + 1)
        assert stored.id is not None
        self._by_id[stored.id] = stored
        return stored

    def save(self, user: UserAccount) -> UserAccount:
        assert user.id is not None
        self._by_id[user.id] = user
        return user


class FakeEventRepository:
    def __init__(self) -> None:
        self._events: dict[int, Event] = {}
        self._next_id = 1
        self.max_session_capacities: dict[int, int] = {}
        self.session_bounds_by_event: dict[int, tuple[datetime, datetime]] = {}
        self.registrations: dict[int, int] = {}

    def add(self, event: Event) -> Event:
        event.id = self._next_id
        self._next_id += 1
        self._events[event.id] = event
        return event

    def get(self, event_id: int) -> Event | None:
        return self._events.get(event_id)

    def list_page(self, filters: EventFilters, page: int, size: int) -> tuple[list[Event], int]:
        matching = [e for e in self._events.values() if self._matches(e, filters)]
        matching.sort(key=lambda e: e.start_at)
        start = (page - 1) * size
        return matching[start : start + size], len(matching)

    @staticmethod
    def _matches(event: Event, filters: EventFilters) -> bool:
        if not filters.unrestricted and not (
            event.status is EventStatus.PUBLISHED or event.organizer_id == filters.viewer_id
        ):
            return False
        if filters.status is not None and event.status is not filters.status:
            return False
        return not filters.q or filters.q.lower() in event.name.lower()

    def update(self, event: Event) -> Event:
        assert event.id is not None
        self._events[event.id] = event
        return event

    def list_published_ended_before(self, moment: datetime) -> list[Event]:
        return [
            e
            for e in self._events.values()
            if e.status is EventStatus.PUBLISHED and ensure_utc(e.end_at) < ensure_utc(moment)
        ]

    def delete(self, event_id: int) -> None:
        self._events.pop(event_id, None)

    def count_registrations(self, event_id: int) -> int:
        return self.registrations.get(event_id, 0)

    def max_session_capacity(self, event_id: int) -> int:
        return self.max_session_capacities.get(event_id, 0)

    def session_bounds(self, event_id: int) -> tuple[datetime, datetime] | None:
        return self.session_bounds_by_event.get(event_id)


class FakeSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[int, Session] = {}
        self._next_id = 1
        self.enrollment_counts: dict[int, int] = {}

    def lock_and_count_enrollments(self, session_id: int) -> int:
        return self.enrollment_counts.get(session_id, 0)

    def add(self, session: Session) -> Session:
        session.id = self._next_id
        self._next_id += 1
        self._sessions[session.id] = session
        return session

    def get(self, session_id: int) -> Session | None:
        return self._sessions.get(session_id)

    def list_for_event(self, event_id: int) -> list[Session]:
        found = [s for s in self._sessions.values() if s.event_id == event_id]
        return sorted(found, key=lambda s: s.start_at)

    def list_for_speaker(self, speaker_id: int) -> list[Session]:
        return [s for s in self._sessions.values() if s.speaker_id == speaker_id]

    def update(self, session: Session) -> Session:
        assert session.id is not None
        self._sessions[session.id] = session
        return session

    def delete(self, session_id: int) -> None:
        self._sessions.pop(session_id, None)


class FakeRegistrationRepository:
    def __init__(
        self, events: FakeEventRepository, users: FakeUserRepository | None = None
    ) -> None:
        self._events = events
        self._users = users or FakeUserRepository()
        self._rows: dict[tuple[int, int], datetime] = {}
        self.cancel_hooks: list[Callable[[int, int], None]] = []

    def register(self, user_id: int, event_id: int, rule: RegistrationRule) -> Registration:
        event = self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        if (user_id, event_id) in self._rows:
            raise AlreadyRegisteredError("Already registered")
        rule(event, self._events.count_registrations(event_id))
        created_at = datetime.now(UTC)
        self._rows[(user_id, event_id)] = created_at
        self._events.registrations[event_id] = self._events.count_registrations(event_id) + 1
        return Registration(user_id=user_id, event_id=event_id, created_at=created_at)

    def is_registered(self, user_id: int, event_id: int) -> bool:
        return (user_id, event_id) in self._rows

    def cancel(self, user_id: int, event_id: int) -> bool:
        if self._rows.pop((user_id, event_id), None) is None:
            return False
        self._events.registrations[event_id] -= 1
        for hook in self.cancel_hooks:
            hook(user_id, event_id)
        return True

    def list_for_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[RegisteredEvent], int]:
        mine = [
            RegisteredEvent(self._events.get(event_id), created_at)  # type: ignore[arg-type]
            for (uid, event_id), created_at in self._rows.items()
            if uid == user_id
        ]
        mine.sort(key=lambda r: r.event.start_at)
        start = (page - 1) * size
        return mine[start : start + size], len(mine)

    def list_participants(
        self, filters: ParticipantFilters, page: int, size: int
    ) -> tuple[list[ParticipantRow], int]:
        matching = list(self.iter_participants(filters))
        start = (page - 1) * size
        return matching[start : start + size], len(matching)

    def iter_participants(self, filters: ParticipantFilters) -> Iterator[ParticipantRow]:
        ordered = sorted(
            self._rows.items(),
            key=lambda row: (
                self._events.get(row[0][1]).start_at,  # type: ignore[union-attr]
                row[0][1],
                row[1],
            ),
        )
        for (user_id, event_id), _ in ordered:
            event = self._events.get(event_id)
            user = self._users.get_by_id(user_id)
            assert event is not None and user is not None
            if self._matches(event, filters):
                yield ParticipantRow(user.full_name, user.email, event.name)

    @staticmethod
    def _matches(event: Event, filters: ParticipantFilters) -> bool:
        if filters.organizer_id is not None and event.organizer_id != filters.organizer_id:
            return False
        if filters.event_id is not None and event.id != filters.event_id:
            return False
        if filters.status is not None and event.status is not filters.status:
            return False
        if filters.q and filters.q.lower() not in event.name.lower():
            return False
        start = ensure_utc(event.start_at)
        if filters.date_from is not None and start < filters.date_from:
            return False
        return filters.date_to is None or start <= filters.date_to


class FakeSessionRegistrationRepository:
    def __init__(
        self,
        events: FakeEventRepository,
        sessions: FakeSessionRepository,
        registrations: FakeRegistrationRepository,
        users: FakeUserRepository | None = None,
    ) -> None:
        self._events = events
        self._sessions = sessions
        self._registrations = registrations
        self._users = users or FakeUserRepository()
        self._rows: dict[tuple[int, int], datetime] = {}
        registrations.cancel_hooks.append(self._drop_event_enrollments)

    def _drop_event_enrollments(self, user_id: int, event_id: int) -> None:
        for session in self._sessions.list_for_event(event_id):
            self._rows.pop((user_id, session.id or 0), None)

    def enroll(self, user_id: int, session_id: int, rule: EnrollmentRule) -> SessionRegistration:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        event = self._events.get(session.event_id)
        assert event is not None
        if (user_id, session_id) in self._rows:
            raise AlreadyEnrolledError("Already enrolled")
        mine = [
            other
            for (uid, sid) in self._rows
            if uid == user_id and (other := self._sessions.get(sid)) is not None
        ]
        rule(
            EnrollmentContext(
                event=event,
                session=session,
                event_registered=self._registrations.is_registered(user_id, event.id or 0),
                enrolled_sessions=mine,
                enrolled_count=self._count(session_id),
            )
        )
        created_at = datetime.now(UTC)
        self._rows[(user_id, session_id)] = created_at
        return SessionRegistration(user_id=user_id, session_id=session_id, created_at=created_at)

    def _count(self, session_id: int) -> int:
        return sum(1 for (_, sid) in self._rows if sid == session_id)

    def is_enrolled(self, user_id: int, session_id: int) -> bool:
        return (user_id, session_id) in self._rows

    def cancel(self, user_id: int, session_id: int) -> bool:
        return self._rows.pop((user_id, session_id), None) is not None

    def counts_for_event(self, event_id: int) -> dict[int, int]:
        return {
            s.id: self._count(s.id)
            for s in self._sessions.list_for_event(event_id)
            if s.id is not None and self._count(s.id)
        }

    def enrolled_session_ids(self, user_id: int, event_id: int) -> set[int]:
        in_event = {s.id for s in self._sessions.list_for_event(event_id)}
        return {sid for (uid, sid) in self._rows if uid == user_id and sid in in_event}

    def list_participants(
        self, filters: SessionParticipantFilters, page: int, size: int
    ) -> tuple[list[SessionParticipantRow], int]:
        matching = list(self.iter_participants(filters))
        start = (page - 1) * size
        return matching[start : start + size], len(matching)

    def iter_participants(
        self, filters: SessionParticipantFilters
    ) -> Iterator[SessionParticipantRow]:
        ordered = sorted(
            self._rows.items(),
            key=lambda row: (
                self._sessions.get(row[0][1]).start_at,  # type: ignore[union-attr]
                row[0][1],
                row[1],
            ),
        )
        for (user_id, session_id), _ in ordered:
            session = self._sessions.get(session_id)
            assert session is not None
            event = self._events.get(session.event_id)
            user = self._users.get_by_id(user_id)
            assert event is not None and user is not None
            if self._matches(event, session, filters):
                yield SessionParticipantRow(
                    user.full_name, user.email, event.name, session.title, session.start_at
                )

    @staticmethod
    def _matches(event: Event, session: Session, filters: SessionParticipantFilters) -> bool:
        if filters.organizer_id is not None and event.organizer_id != filters.organizer_id:
            return False
        if filters.event_id is not None and event.id != filters.event_id:
            return False
        if filters.session_id is not None and session.id != filters.session_id:
            return False
        if filters.status is not None and event.status is not filters.status:
            return False
        if filters.q and not any(
            filters.q.lower() in text.lower() for text in (session.title, event.name)
        ):
            return False
        start = ensure_utc(session.start_at)
        if filters.date_from is not None and start < filters.date_from:
            return False
        return filters.date_to is None or start <= filters.date_to


class FakeSpeakerRepository:
    def __init__(self, sessions: FakeSessionRepository | None = None) -> None:
        self._speakers: dict[int, Speaker] = {}
        self._next_id = 1
        self._sessions = sessions or FakeSessionRepository()

    def add(self, speaker: Speaker) -> Speaker:
        speaker.id = self._next_id
        self._next_id += 1
        self._speakers[speaker.id] = speaker
        return speaker

    def get(self, speaker_id: int) -> Speaker | None:
        return self._speakers.get(speaker_id)

    def get_by_email(self, email: str) -> Speaker | None:
        return next((s for s in self._speakers.values() if s.email == email), None)

    def list_page(self, q: str | None, page: int, size: int) -> tuple[list[Speaker], int]:
        term = q.lower() if q else None
        matching = [s for s in self._speakers.values() if term is None or term in s.name.lower()]
        matching.sort(key=lambda s: (s.name, s.id or 0))
        start = (page - 1) * size
        return matching[start : start + size], len(matching)

    def update(self, speaker: Speaker) -> Speaker:
        assert speaker.id is not None
        self._speakers[speaker.id] = speaker
        return speaker

    def delete(self, speaker_id: int) -> None:
        self._speakers.pop(speaker_id, None)

    def count_sessions(self, speaker_id: int) -> int:
        return len(self._sessions.list_for_speaker(speaker_id))


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{password}"


class FakeTokenService:
    def create_access_token(self, user_id: int) -> str:
        return f"token-{user_id}"

    def read_subject(self, token: str) -> int:
        if not token.startswith("token-"):
            raise InvalidTokenError
        return int(token.removeprefix("token-"))


class FakeCache:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], str] = {}
        self.sets: list[tuple[str, str, str, int]] = []
        self.invalidations: list[str] = []

    def get(self, namespace: str, key: str) -> str | None:
        return self._entries.get((namespace, key))

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int) -> None:
        self._entries[(namespace, key)] = value
        self.sets.append((namespace, key, value, ttl_seconds))

    def invalidate(self, namespace: str) -> None:
        self.invalidations.append(namespace)
        self._entries = {
            entry: value for entry, value in self._entries.items() if entry[0] != namespace
        }


class UnreachableRedis:
    def get(self, name: str) -> str | None:
        raise redis.ConnectionError("redis is down")

    def setex(self, name: str, time: int, value: str) -> None:
        raise redis.ConnectionError("redis is down")

    def incr(self, name: str) -> int:
        raise redis.ConnectionError("redis is down")
