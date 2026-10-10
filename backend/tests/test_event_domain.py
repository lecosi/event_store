from datetime import UTC, datetime, timedelta

import pytest

from app.domain.enums import EventStatus
from app.domain.event import (
    EventPage,
    EventStateError,
    EventValidationError,
    ensure_editable,
    validate_capacity,
    validate_schedule,
    validate_starts_in_future,
    validate_transition,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (EventStatus.DRAFT, EventStatus.PUBLISHED),
        (EventStatus.PUBLISHED, EventStatus.FINISHED),
        (EventStatus.DRAFT, EventStatus.CANCELLED),
        (EventStatus.PUBLISHED, EventStatus.CANCELLED),
    ],
)
def test_valid_transitions(current: EventStatus, target: EventStatus) -> None:
    validate_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (EventStatus.DRAFT, EventStatus.FINISHED),
        (EventStatus.DRAFT, EventStatus.DRAFT),
        (EventStatus.PUBLISHED, EventStatus.DRAFT),
        (EventStatus.CANCELLED, EventStatus.PUBLISHED),
        (EventStatus.CANCELLED, EventStatus.DRAFT),
        (EventStatus.FINISHED, EventStatus.CANCELLED),
        (EventStatus.FINISHED, EventStatus.PUBLISHED),
    ],
)
def test_invalid_transitions(current: EventStatus, target: EventStatus) -> None:
    with pytest.raises(EventStateError):
        validate_transition(current, target)


def test_schedule_requires_end_after_start() -> None:
    validate_schedule(NOW, NOW + timedelta(hours=1))
    with pytest.raises(EventValidationError):
        validate_schedule(NOW, NOW)
    with pytest.raises(EventValidationError):
        validate_schedule(NOW, NOW - timedelta(hours=1))


def test_schedule_handles_naive_and_aware_datetimes() -> None:
    validate_schedule(NOW.replace(tzinfo=None), NOW + timedelta(hours=1))


def test_capacity_must_be_positive() -> None:
    validate_capacity(1)
    with pytest.raises(EventValidationError):
        validate_capacity(0)


def test_start_must_be_in_future() -> None:
    validate_starts_in_future(NOW + timedelta(seconds=1), NOW)
    with pytest.raises(EventValidationError):
        validate_starts_in_future(NOW, NOW)


@pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.FINISHED])
def test_closed_events_are_not_editable(status: EventStatus) -> None:
    with pytest.raises(EventStateError):
        ensure_editable(status)


@pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.PUBLISHED])
def test_open_events_are_editable(status: EventStatus) -> None:
    ensure_editable(status)


@pytest.mark.parametrize(
    ("total", "size", "pages"), [(0, 10, 0), (1, 10, 1), (10, 10, 1), (11, 10, 2), (25, 10, 3)]
)
def test_page_count(total: int, size: int, pages: int) -> None:
    assert EventPage(items=[], total=total, page=1, size=size).pages == pages
