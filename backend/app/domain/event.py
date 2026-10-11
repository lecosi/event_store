"""Event aggregate and business rules (pure domain, no framework imports)."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from math import ceil

from app.domain.enums import EventStatus


class EventValidationError(ValueError):
    """The event data violates a business rule (maps to HTTP 422)."""


class EventStateError(Exception):
    """The operation conflicts with the event's current state (maps to HTTP 409)."""


ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.DRAFT: frozenset({EventStatus.PUBLISHED, EventStatus.CANCELLED}),
    EventStatus.PUBLISHED: frozenset({EventStatus.FINISHED, EventStatus.CANCELLED}),
    EventStatus.CANCELLED: frozenset(),
    EventStatus.FINISHED: frozenset(),
}


@dataclass(frozen=True)
class EventDetails:
    """Editable attributes of an event."""

    name: str
    description: str
    location: str
    start_at: datetime
    end_at: datetime
    capacity: int


@dataclass
class Event:
    name: str
    description: str
    location: str
    start_at: datetime
    end_at: datetime
    capacity: int
    organizer_id: int
    status: EventStatus = EventStatus.DRAFT
    id: int | None = None

    def with_details(self, details: EventDetails) -> "Event":
        return replace(
            self,
            name=details.name,
            description=details.description,
            location=details.location,
            start_at=details.start_at,
            end_at=details.end_at,
            capacity=details.capacity,
        )


@dataclass(frozen=True)
class EventFilters:
    """Criteria for listing events.

    ``unrestricted`` lets the caller see every status; otherwise only PUBLISHED
    events plus the ones owned by ``viewer_id`` are visible.
    """

    q: str | None = None
    status: EventStatus | None = None
    viewer_id: int | None = None
    unrestricted: bool = False


@dataclass(frozen=True)
class ParticipantFilters:
    """Criteria for the participants report.

    ``date_from`` / ``date_to`` are inclusive bounds on the event start, already expressed as
    UTC instants. ``organizer_id`` restricts the report to that organizer's events; ``None``
    means unrestricted (admin).
    """

    organizer_id: int | None = None
    event_id: int | None = None
    q: str | None = None
    status: EventStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True)
class EventPage:
    items: list[Event]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size) if self.total else 0


def ensure_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never mix naive and aware values."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def validate_schedule(start_at: datetime, end_at: datetime) -> None:
    if ensure_utc(end_at) <= ensure_utc(start_at):
        raise EventValidationError("end_at must be after start_at")


def validate_capacity(capacity: int) -> None:
    if capacity < 1:
        raise EventValidationError("capacity must be at least 1")


def validate_starts_in_future(start_at: datetime, now: datetime) -> None:
    if ensure_utc(start_at) <= ensure_utc(now):
        raise EventValidationError("start_at must be in the future")


def validate_details(details: EventDetails) -> None:
    validate_schedule(details.start_at, details.end_at)
    validate_capacity(details.capacity)


def ensure_editable(status: EventStatus) -> None:
    if status in (EventStatus.CANCELLED, EventStatus.FINISHED):
        raise EventStateError(f"A {status.value} event cannot be edited")


def ensure_capacity_covers_sessions(capacity: int, largest_session: int) -> None:
    if capacity < largest_session:
        raise EventStateError(
            f"capacity cannot be lower than the largest session capacity ({largest_session})"
        )


def ensure_capacity_covers_registrations(capacity: int, registrations: int) -> None:
    if capacity < registrations:
        raise EventStateError(
            f"capacity cannot be lower than the current registrations ({registrations})"
        )


def ensure_dates_cover_sessions(
    start_at: datetime,
    end_at: datetime,
    session_bounds: tuple[datetime, datetime] | None,
) -> None:
    """Reject new event dates that would leave an existing session outside them."""
    if session_bounds is None:
        return
    first_start, last_end = session_bounds
    if ensure_utc(start_at) > ensure_utc(first_start) or ensure_utc(end_at) < ensure_utc(last_end):
        raise EventStateError("event dates must still contain all of its existing sessions")


def can_view(event: Event, viewer_id: int | None, is_admin: bool) -> bool:
    """Published events are public; the rest only for their organizer or an admin."""
    if event.status is EventStatus.PUBLISHED:
        return True
    return viewer_id is not None and (is_admin or event.organizer_id == viewer_id)


def validate_transition(current: EventStatus, target: EventStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise EventStateError(f"Cannot change status from {current.value} to {target.value}")
