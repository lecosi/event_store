"""Registration rules (pure domain, no framework imports)."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import EventStatus
from app.domain.event import Event, ensure_utc


class RegistrationConflictError(Exception):
    """The registration conflicts with the current state (maps to HTTP 409)."""


class AlreadyRegisteredError(RegistrationConflictError):
    pass


class EventFullError(RegistrationConflictError):
    pass


class RegistrationClosedError(RegistrationConflictError):
    """The event no longer accepts (or allows cancelling) registrations."""


class NotRegisteredError(Exception):
    """The user has no registration for the event (maps to HTTP 404)."""


@dataclass(frozen=True)
class Registration:
    user_id: int
    event_id: int
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class RegisteredEvent:
    """An event together with when the user registered to it."""

    event: Event
    registered_at: datetime


@dataclass(frozen=True)
class RegisteredEventPage:
    items: list[RegisteredEvent]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return -(-self.total // self.size) if self.total else 0


@dataclass(frozen=True)
class Availability:
    registered_count: int
    available_spots: int
    is_registered: bool


def available_spots(capacity: int, registered: int) -> int:
    return max(capacity - registered, 0)


def ensure_can_register(event: Event, registered: int, now: datetime) -> None:
    if event.status is not EventStatus.PUBLISHED:
        raise RegistrationClosedError("Only published events accept registrations")
    if ensure_utc(event.end_at) <= ensure_utc(now):
        raise RegistrationClosedError("The event has already ended")
    if registered >= event.capacity:
        raise EventFullError("The event is full")


def ensure_can_cancel(event: Event) -> None:
    if event.status is EventStatus.FINISHED:
        raise RegistrationClosedError("A finished event does not allow cancelling")
