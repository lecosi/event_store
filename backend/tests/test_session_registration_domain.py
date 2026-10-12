from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import EventStatus
from app.domain.event import Event
from app.domain.session import Session
from app.domain.session_registration import (
    EnrollmentClosedError,
    EnrollmentContext,
    EventRegistrationRequiredError,
    ScheduleConflictError,
    SessionFullError,
    ensure_can_cancel_enrollment,
    ensure_can_enroll,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def make_event(status: EventStatus = EventStatus.PUBLISHED, ends_in_hours: int = 48) -> Event:
    return Event(
        id=1,
        name="PyCon",
        description="",
        location="Lima",
        start_at=NOW - timedelta(hours=1),
        end_at=NOW + timedelta(hours=ends_in_hours),
        capacity=10,
        organizer_id=9,
        status=status,
    )


def make_session(
    start_hours: int, end_hours: int, session_id: int = 1, capacity: int = 2
) -> Session:
    return Session(
        id=session_id,
        event_id=1,
        speaker_id=1,
        title="Talk",
        start_at=NOW + timedelta(hours=start_hours),
        end_at=NOW + timedelta(hours=end_hours),
        capacity=capacity,
    )


def context(
    event: Event | None = None,
    session: Session | None = None,
    event_registered: bool = True,
    enrolled: list[Session] | None = None,
    enrolled_count: int = 0,
) -> EnrollmentContext:
    return EnrollmentContext(
        event=event or make_event(),
        session=session or make_session(1, 2),
        event_registered=event_registered,
        enrolled_sessions=enrolled or [],
        enrolled_count=enrolled_count,
    )


def test_enrollment_is_allowed_with_free_seats_and_no_overlap() -> None:
    ensure_can_enroll(context(enrolled=[make_session(3, 4, session_id=2)], enrolled_count=1), NOW)


def test_enrollment_is_rejected_when_the_event_is_not_published() -> None:
    with pytest.raises(EnrollmentClosedError):
        ensure_can_enroll(context(event=make_event(EventStatus.DRAFT)), NOW)


def test_enrollment_is_rejected_when_the_event_has_ended() -> None:
    with pytest.raises(EnrollmentClosedError):
        ensure_can_enroll(context(event=make_event(ends_in_hours=-1)), NOW)


def test_enrollment_is_rejected_when_the_session_has_ended() -> None:
    with pytest.raises(EnrollmentClosedError):
        ensure_can_enroll(context(session=make_session(-3, -2)), NOW)


def test_enrollment_requires_the_event_registration() -> None:
    with pytest.raises(EventRegistrationRequiredError):
        ensure_can_enroll(context(event_registered=False), NOW)


def test_enrollment_is_rejected_when_the_session_is_full() -> None:
    with pytest.raises(SessionFullError):
        ensure_can_enroll(context(enrolled_count=2), NOW)


def test_enrollment_is_rejected_when_it_overlaps_another_enrolled_session() -> None:
    other = make_session(1, 3, session_id=2)
    with pytest.raises(ScheduleConflictError):
        ensure_can_enroll(context(enrolled=[other]), NOW)


def test_back_to_back_sessions_do_not_overlap() -> None:
    ensure_can_enroll(context(enrolled=[make_session(2, 3, session_id=2)]), NOW)


def test_cancelling_is_allowed_while_the_event_is_published() -> None:
    ensure_can_cancel_enrollment(make_event())


def test_cancelling_is_rejected_when_the_event_is_finished() -> None:
    with pytest.raises(EnrollmentClosedError):
        ensure_can_cancel_enrollment(make_event(EventStatus.FINISHED))
