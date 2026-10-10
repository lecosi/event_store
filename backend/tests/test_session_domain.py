from datetime import UTC, datetime, timedelta

import pytest

from app.domain.session import (
    Session,
    SessionConflictError,
    SessionValidationError,
    ensure_speaker_available,
    ensure_within_event,
    overlaps,
    validate_session_capacity,
    validate_session_times,
)

T0 = datetime(2030, 1, 1, 10, tzinfo=UTC)


def hours(n: int) -> datetime:
    return T0 + timedelta(hours=n)


def session(start: int, end: int, id: int | None = None) -> Session:
    return Session(
        event_id=1,
        speaker_id=1,
        title="Talk",
        start_at=hours(start),
        end_at=hours(end),
        capacity=5,
        id=id,
    )


def test_end_must_be_after_start() -> None:
    validate_session_times(hours(0), hours(1))
    with pytest.raises(SessionValidationError):
        validate_session_times(hours(1), hours(1))
    with pytest.raises(SessionValidationError):
        validate_session_times(hours(2), hours(1))


def test_session_must_fit_inside_event() -> None:
    ensure_within_event(hours(0), hours(4), hours(0), hours(4))
    with pytest.raises(SessionValidationError):
        ensure_within_event(hours(-1), hours(2), hours(0), hours(4))
    with pytest.raises(SessionValidationError):
        ensure_within_event(hours(2), hours(5), hours(0), hours(4))


def test_naive_and_aware_datetimes_compare_as_utc() -> None:
    naive = datetime(2030, 1, 1, 10)
    ensure_within_event(naive, naive + timedelta(hours=1), hours(0), hours(4))


def test_capacity_bounds() -> None:
    validate_session_capacity(1, 10)
    validate_session_capacity(10, 10)
    with pytest.raises(SessionValidationError):
        validate_session_capacity(0, 10)
    with pytest.raises(SessionValidationError):
        validate_session_capacity(11, 10)


def test_overlaps_detects_partial_contained_and_ignores_adjacent() -> None:
    assert overlaps(hours(0), hours(2), hours(1), hours(3))
    assert overlaps(hours(0), hours(4), hours(1), hours(2))
    assert not overlaps(hours(0), hours(1), hours(1), hours(2))
    assert not overlaps(hours(2), hours(3), hours(0), hours(2))


def test_speaker_overlap_is_a_conflict() -> None:
    with pytest.raises(SessionConflictError):
        ensure_speaker_available(session(1, 3), [session(0, 2, id=9)])


def test_adjacent_sessions_are_allowed() -> None:
    ensure_speaker_available(session(2, 3), [session(0, 2, id=9), session(3, 4, id=10)])


def test_candidate_is_excluded_from_its_own_comparison() -> None:
    ensure_speaker_available(session(0, 2, id=9), [session(0, 2, id=9)])
