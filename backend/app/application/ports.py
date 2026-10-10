"""Ports (abstractions) that the application layer depends on.

Infrastructure provides the implementations; use cases receive them by injection.
Each port is small and focused (interface segregation).
"""

from datetime import datetime
from typing import Protocol

from app.domain.enums import Role
from app.domain.event import Event, EventFilters
from app.domain.session import Session
from app.domain.speaker import Speaker
from app.domain.user import UserAccount


class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> UserAccount | None: ...

    def get_by_email(self, email: str) -> UserAccount | None: ...

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        """Persist a new user; raise EmailAlreadyRegisteredError on duplicate email."""
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


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: int) -> str: ...

    def read_subject(self, token: str) -> int:
        """Return the user id carried by the token; raise InvalidTokenError otherwise."""
        ...
