from datetime import UTC, datetime

from app.application.errors import (
    EmailAlreadyRegisteredError,
    EventNotFoundError,
    InvalidTokenError,
)
from app.application.ports import RegistrationRule
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventFilters
from app.domain.registration import AlreadyRegisteredError, RegisteredEvent, Registration
from app.domain.session import Session
from app.domain.speaker import Speaker
from app.domain.user import UserAccount


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, UserAccount] = {}

    def get_by_id(self, user_id: int) -> UserAccount | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> UserAccount | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        if self.get_by_email(email):
            raise EmailAlreadyRegisteredError(email)
        user = UserAccount(
            email=email, password_hash=password_hash, role=role, id=len(self._by_id) + 1
        )
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
    def __init__(self, events: FakeEventRepository) -> None:
        self._events = events
        self._rows: dict[tuple[int, int], datetime] = {}

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
