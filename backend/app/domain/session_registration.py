"""Session enrollment rules (pure domain, no framework imports)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import EventStatus
from app.domain.event import Event, ensure_utc
from app.domain.registration import RegistrationConflictError
from app.domain.session import Session, overlaps


class EnrollmentConflictError(RegistrationConflictError):
    """The enrollment conflicts with the current state (maps to HTTP 409)."""


class SessionFullError(EnrollmentConflictError):
    pass


class AlreadyEnrolledError(EnrollmentConflictError):
    pass


class EventRegistrationRequiredError(EnrollmentConflictError):
    """The user must register to the event before enrolling in one of its sessions."""


class EnrollmentClosedError(EnrollmentConflictError):
    """The session no longer accepts (or allows cancelling) enrollments."""


class ScheduleConflictError(EnrollmentConflictError):
    """The session overlaps another session the user is already enrolled in."""


class NotEnrolledError(Exception):
    """The user is not enrolled in the session (maps to HTTP 404)."""


@dataclass(frozen=True)
class SessionRegistration:
    user_id: int
    session_id: int
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True)
class SessionParticipantFilters:
    """Criteria for the session participants report.

    ``date_from`` / ``date_to`` are inclusive bounds on the session start, already expressed
    as UTC instants. ``organizer_id`` restricts the report to that organizer's events;
    ``None`` means unrestricted (admin). ``status`` is the status of the session's event.
    """

    organizer_id: int | None = None
    event_id: int | None = None
    session_id: int | None = None
    q: str | None = None
    status: EventStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True)
class SessionParticipantRow:
    """One person enrolled in one session, as listed in the session participants report."""

    full_name: str
    email: str
    event_name: str
    session_title: str
    session_start: datetime


@dataclass(frozen=True)
class SessionParticipantPage:
    items: list[SessionParticipantRow]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return -(-self.total // self.size) if self.total else 0


@dataclass(frozen=True)
class SessionAvailability:
    enrolled_count: int
    available_spots: int
    is_enrolled: bool


@dataclass(frozen=True)
class EnrollmentContext:
    """What the enrollment rule needs, read while the session row is locked."""

    event: Event
    session: Session
    event_registered: bool
    enrolled_sessions: Iterable[Session]
    enrolled_count: int


def ensure_can_enroll(context: EnrollmentContext, now: datetime) -> None:
    event, session = context.event, context.session
    if event.status is not EventStatus.PUBLISHED:
        raise EnrollmentClosedError("Only sessions of published events accept enrollments")
    if ensure_utc(event.end_at) <= ensure_utc(now):
        raise EnrollmentClosedError("The event has already ended")
    if ensure_utc(session.end_at) <= ensure_utc(now):
        raise EnrollmentClosedError("The session has already ended")
    if not context.event_registered:
        raise EventRegistrationRequiredError("Register to the event before enrolling in a session")
    for other in context.enrolled_sessions:
        if other.id != session.id and overlaps(
            session.start_at, session.end_at, other.start_at, other.end_at
        ):
            raise ScheduleConflictError("The session overlaps another session you are enrolled in")
    if context.enrolled_count >= session.capacity:
        raise SessionFullError("The session is full")


def ensure_can_cancel_enrollment(event: Event) -> None:
    if event.status is EventStatus.FINISHED:
        raise EnrollmentClosedError("A finished event does not allow cancelling")
