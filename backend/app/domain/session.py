"""Session aggregate and schedule/capacity rules (pure domain, no framework imports)."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from app.domain.event import EventStateError, ensure_utc


class SessionValidationError(ValueError):
    """The session data violates a business rule (maps to HTTP 422)."""


class SessionConflictError(Exception):
    """The session collides with another one of the same speaker (maps to HTTP 409)."""


@dataclass(frozen=True)
class SessionDetails:
    """Editable attributes of a session."""

    title: str
    speaker_id: int
    start_at: datetime
    end_at: datetime
    capacity: int


@dataclass
class Session:
    event_id: int
    speaker_id: int
    title: str
    start_at: datetime
    end_at: datetime
    capacity: int
    id: int | None = None

    def with_details(self, details: SessionDetails) -> "Session":
        return replace(
            self,
            title=details.title,
            speaker_id=details.speaker_id,
            start_at=details.start_at,
            end_at=details.end_at,
            capacity=details.capacity,
        )


@dataclass(frozen=True)
class SessionWithSpeaker:
    """A session enriched with the display name of its speaker."""

    session: Session
    speaker_name: str


def validate_session_times(start_at: datetime, end_at: datetime) -> None:
    if ensure_utc(end_at) <= ensure_utc(start_at):
        raise SessionValidationError("end_at must be after start_at")


def ensure_within_event(
    start_at: datetime, end_at: datetime, event_start: datetime, event_end: datetime
) -> None:
    if ensure_utc(start_at) < ensure_utc(event_start) or ensure_utc(end_at) > ensure_utc(event_end):
        raise SessionValidationError("session must take place within the event's dates")


def validate_session_capacity(capacity: int, event_capacity: int) -> None:
    if capacity < 1:
        raise SessionValidationError("capacity must be at least 1")
    if capacity > event_capacity:
        raise SessionValidationError(
            f"capacity cannot exceed the event capacity ({event_capacity})"
        )


def ensure_capacity_covers_enrollments(capacity: int, enrollments: int) -> None:
    if capacity < enrollments:
        raise EventStateError(
            f"capacity cannot be lower than the current enrollments ({enrollments})"
        )


def ensure_schedule_unchanged(current: Session, updated: Session) -> None:
    if ensure_utc(current.start_at) != ensure_utc(updated.start_at) or ensure_utc(
        current.end_at
    ) != ensure_utc(updated.end_at):
        raise EventStateError("the schedule of a session with enrollments cannot be changed")


def ensure_deletable_without_enrollments(enrollments: int) -> None:
    if enrollments > 0:
        raise EventStateError("a session with enrollments cannot be deleted")


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Half-open interval overlap: sessions that merely touch do not overlap."""
    return ensure_utc(a_start) < ensure_utc(b_end) and ensure_utc(b_start) < ensure_utc(a_end)


def ensure_speaker_available(candidate: Session, speaker_sessions: Iterable[Session]) -> None:
    """Reject the candidate when its speaker already has an overlapping session.

    The candidate itself (same id) is ignored so that updates can keep their slot.
    """
    for other in speaker_sessions:
        if candidate.id is not None and other.id == candidate.id:
            continue
        if overlaps(candidate.start_at, candidate.end_at, other.start_at, other.end_at):
            raise SessionConflictError("the speaker already has a session in that time slot")
