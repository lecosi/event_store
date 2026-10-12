"""Ports (abstractions) that the application layer depends on.

Infrastructure provides the implementations; use cases receive them by injection.
Each port is small and focused (interface segregation): a use case depends only on the
ports for the roles it actually plays, even when one adapter implements several of them.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol

from app.domain.event import Event, EventFilters, ParticipantFilters
from app.domain.registration import ParticipantRow, RegisteredEvent, Registration
from app.domain.session import Session
from app.domain.session_registration import (
    EnrollmentContext,
    SessionParticipantFilters,
    SessionParticipantRow,
    SessionRegistration,
)
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

    def list_page(self, page: int, size: int) -> tuple[list[UserAccount], int]:
        """Return the requested page (ordered by id) and the total number of users."""
        ...

    def add(self, user: UserAccount) -> UserAccount:
        """Stage a new user; raise EmailAlreadyRegisteredError on duplicate email."""
        ...

    def save(self, user: UserAccount) -> UserAccount:
        """Stage changes to an existing user; raise EmailAlreadyRegisteredError on duplicate."""
        ...


class EventRepository(Protocol):
    def add(self, event: Event) -> Event: ...

    def get(self, event_id: int) -> Event | None: ...

    def list_page(self, filters: EventFilters, page: int, size: int) -> tuple[list[Event], int]:
        """Return the requested page (ordered by start_at) and the total matching count."""
        ...

    def update(self, event: Event) -> Event: ...

    def list_published_ended_before(self, moment: datetime) -> list[Event]:
        """Return the PUBLISHED events whose ``end_at`` is strictly before ``moment``.

        Implementations lock the returned rows until the unit of work ends, so a concurrent
        status change cannot be overwritten by the caller's update.
        """
        ...

    def delete(self, event_id: int) -> None:
        """Delete the event together with its dependent rows."""
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


class EventUsageQueries(Protocol):
    """Read-only questions about what depends on an event, across aggregates."""

    def count_registrations(self, event_id: int) -> int: ...

    def max_session_capacity(self, event_id: int) -> int:
        """Largest capacity among the event's sessions (0 when it has none)."""
        ...

    def session_bounds(self, event_id: int) -> tuple[datetime, datetime] | None:
        """Earliest session start and latest session end (None when it has no sessions)."""
        ...


class SpeakerUsageQueries(Protocol):
    """Read-only questions about what depends on a speaker, across aggregates."""

    def count_sessions(self, speaker_id: int) -> int: ...


class EventAccess(Protocol):
    def ensure_can_manage(self, actor: UserAccount, event_id: int) -> Event:
        """Return the event when ``actor`` owns it or is an admin; raise otherwise."""
        ...


class SessionEnrollmentLock(Protocol):
    def lock_and_count_enrollments(self, session_id: int) -> int:
        """Lock the session row until the unit of work ends and return its enrollment count.

        Concurrent enrollments to the session are serialized behind the lock, so the count
        cannot change before the surrounding update or delete is durable.
        """
        ...


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
        """Delete the registration row only; return False when there was none.

        The user's session enrollments of that event are removed separately through
        ``SessionEnrollmentWriter.cancel_for_event``.
        """
        ...

    def list_for_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[RegisteredEvent], int]:
        """Return the page of the user's events (ordered by start_at) and the total."""
        ...

    def list_participants(
        self, filters: ParticipantFilters, page: int, size: int
    ) -> tuple[list[ParticipantRow], int]:
        """Return the requested page of participants and the total matching count.

        Ordered by event start, event id, registration date and registration id.
        """
        ...

    def iter_participants(self, filters: ParticipantFilters) -> Iterator[ParticipantRow]:
        """Yield every matching participant in the same order, reading in bounded chunks."""
        ...


EnrollmentRule = Callable[[EnrollmentContext], None]
"""Domain rule evaluated with the locked session and the user's enrollment state."""


class SessionEnrollmentWriter(Protocol):
    """Stages enrollment changes and answers the checks that guard them."""

    def enroll(self, user_id: int, session_id: int, rule: EnrollmentRule) -> SessionRegistration:
        """Check ``rule`` against the locked session and stage the enrollment.

        Implementations must serialize concurrent calls for the same session, holding
        the lock until the unit of work ends, so the count seen by ``rule`` cannot
        change before the enrollment is durable. Raise SessionNotFoundError for a
        missing session and AlreadyEnrolledError on a duplicate (checked before
        ``rule``); propagate whatever ``rule`` raises.
        """
        ...

    def is_enrolled(self, user_id: int, session_id: int) -> bool: ...

    def cancel(self, user_id: int, session_id: int) -> bool:
        """Delete the enrollment; return False when there was none."""
        ...

    def cancel_for_event(self, user_id: int, event_id: int) -> int:
        """Delete the user's enrollments in every session of the event; return how many.

        Must run after the event registration is deleted, so that the delete first waits
        for a concurrent ``enroll`` holding the registration row lock and then includes it.
        """
        ...


class SessionAvailabilityReader(Protocol):
    def counts_for_event(self, event_id: int) -> dict[int, int]:
        """Enrollments per session id for the event's sessions (absent ids have none)."""
        ...

    def enrolled_session_ids(self, user_id: int, event_id: int) -> set[int]:
        """Ids of the event's sessions the user is enrolled in."""
        ...


class SessionParticipantQueries(Protocol):
    def list_participants(
        self, filters: SessionParticipantFilters, page: int, size: int
    ) -> tuple[list[SessionParticipantRow], int]:
        """Return the requested page of enrolled people and the total matching count.

        Ordered by session start, session id, enrollment date and enrollment id.
        """
        ...

    def iter_participants(
        self, filters: SessionParticipantFilters
    ) -> Iterator[SessionParticipantRow]:
        """Yield every matching enrolled person in the same order, reading in bounded chunks."""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: int) -> str: ...

    def read_subject(self, token: str) -> int:
        """Return the user id carried by the token; raise InvalidTokenError otherwise."""
        ...
