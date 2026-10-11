"""Ports (abstractions) that the application layer depends on.

Infrastructure provides the implementations; use cases receive them by injection.
Each port is small and focused (interface segregation).
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol

from app.domain.event import Event, EventFilters
from app.domain.registration import RegisteredEvent, Registration
from app.domain.session import Session
from app.domain.speaker import Speaker
from app.domain.user import UserAccount


class UnitOfWork(Protocol):
    """Transaction boundary shared by the repositories of one use case.

    Repositories only stage writes; the use case decides when they become durable.
    """

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@contextmanager
def transaction(uow: UnitOfWork) -> Iterator[None]:
    """Commit once when the block succeeds; roll back and re-raise when it fails."""
    try:
        yield
    except Exception:
        uow.rollback()
        raise
    uow.commit()


EVENTS_NAMESPACE = "events"
SESSIONS_NAMESPACE = "sessions"
SPEAKERS_NAMESPACE = "speakers"


class Cache(Protocol):
    """Namespaced read cache. Implementations never raise: failures behave as misses."""

    def get(self, namespace: str, key: str) -> str | None: ...

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int) -> None: ...

    def invalidate(self, namespace: str) -> None:
        """Make every entry stored so far under ``namespace`` unreachable."""
        ...


class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> UserAccount | None: ...

    def get_by_email(self, email: str) -> UserAccount | None: ...

    def list_all(self) -> list[UserAccount]: ...

    def list_page(self, page: int, size: int) -> tuple[list[UserAccount], int]:
        """Return the requested page (ordered by id) and the total number of users."""
        ...

    def add(self, user: UserAccount) -> UserAccount:
        """Stage a new user; raise EmailAlreadyRegisteredError on duplicate email."""
        ...

    def save(self, user: UserAccount) -> UserAccount:
        """Stage changes to an existing user."""
        ...


class EventRepository(Protocol):
    def add(self, event: Event) -> Event: ...

    def get(self, event_id: int) -> Event | None: ...

    def list_page(self, filters: EventFilters, page: int, size: int) -> tuple[list[Event], int]:
        """Return the requested page (ordered by start_at) and the total matching count."""
        ...

    def update(self, event: Event) -> Event: ...

    def delete(self, event_id: int) -> None:
        """Delete the event together with its dependent rows."""
        ...

    def count_registrations(self, event_id: int) -> int: ...

    def max_session_capacity(self, event_id: int) -> int:
        """Largest capacity among the event's sessions (0 when it has none)."""
        ...

    def session_bounds(self, event_id: int) -> tuple[datetime, datetime] | None:
        """Earliest session start and latest session end (None when it has no sessions)."""
        ...


class SpeakerRepository(Protocol):
    def add(self, speaker: Speaker) -> Speaker: ...

    def get(self, speaker_id: int) -> Speaker | None: ...

    def get_by_email(self, email: str) -> Speaker | None: ...

    def list_page(self, q: str | None, page: int, size: int) -> tuple[list[Speaker], int]:
        """Return the requested page (ordered by name, id) and the total matching speakers.

        ``q`` is a case-insensitive substring match on the name; wildcards match literally.
        """
        ...

    def update(self, speaker: Speaker) -> Speaker: ...

    def delete(self, speaker_id: int) -> None: ...

    def count_sessions(self, speaker_id: int) -> int: ...


class SessionRepository(Protocol):
    def add(self, session: Session) -> Session: ...

    def get(self, session_id: int) -> Session | None: ...

    def list_for_event(self, event_id: int) -> list[Session]:
        """Return the event's sessions ordered by start time."""
        ...

    def list_for_speaker(self, speaker_id: int) -> list[Session]:
        """Return every session of the speaker, across all events."""
        ...

    def update(self, session: Session) -> Session: ...

    def delete(self, session_id: int) -> None: ...


RegistrationRule = Callable[[Event, int], None]
"""Domain rule evaluated with the (locked) event and its current registration count."""


class RegistrationRepository(Protocol):
    def register(self, user_id: int, event_id: int, rule: RegistrationRule) -> Registration:
        """Check ``rule`` against the locked event and stage the registration.

        Implementations must serialize concurrent calls for the same event, holding
        the lock until the unit of work ends, so the count seen by ``rule`` cannot
        change before the registration is durable. Raise EventNotFoundError for a
        missing event and AlreadyRegisteredError on a duplicate (checked before
        ``rule``); propagate whatever ``rule`` raises.
        """
        ...

    def is_registered(self, user_id: int, event_id: int) -> bool: ...

    def cancel(self, user_id: int, event_id: int) -> bool:
        """Delete the registration; return False when there was none."""
        ...

    def list_for_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[RegisteredEvent], int]:
        """Return the page of the user's events (ordered by start_at) and the total."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: int) -> str: ...

    def read_subject(self, token: str) -> int:
        """Return the user id carried by the token; raise InvalidTokenError otherwise."""
        ...
