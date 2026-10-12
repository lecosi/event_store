from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import EventNotFoundError
from app.application.registration_service import RegistrationService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event
from app.domain.registration import (
    AlreadyRegisteredError,
    EventFullError,
    NotRegisteredError,
    RegistrationClosedError,
)
from app.domain.user import UserAccount
from tests.fakes import (
    FakeEventRepository,
    FakeRegistrationRepository,
    FakeSessionRegistrationRepository,
    FakeSessionRepository,
    FakeUnitOfWork,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def user(user_id: int, role: Role = Role.ATTENDEE) -> UserAccount:
    return UserAccount(
        id=user_id, email=f"u{user_id}@x.com", full_name="Test User", password_hash="h", role=role
    )


@pytest.fixture
def events() -> FakeEventRepository:
    return FakeEventRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def service(events: FakeEventRepository, uow: FakeUnitOfWork) -> RegistrationService:
    registrations = FakeRegistrationRepository(events)
    enrollments = FakeSessionRegistrationRepository(events, FakeSessionRepository(), registrations)
    return RegistrationService(events, registrations, enrollments, uow, clock=lambda: NOW)


def add_event(
    events: FakeEventRepository,
    status: EventStatus = EventStatus.PUBLISHED,
    capacity: int = 2,
    days: int = 1,
) -> Event:
    return events.add(
        Event(
            name="PyCon",
            description="",
            location="Lima",
            start_at=NOW + timedelta(days=days),
            end_at=NOW + timedelta(days=days, hours=5),
            capacity=capacity,
            organizer_id=99,
            status=status,
        )
    )


def test_register_success(service: RegistrationService, events: FakeEventRepository) -> None:
    event = add_event(events)
    result = service.register(user(1), event.id)
    assert (result.user_id, result.event_id) == (1, event.id)
    availability = service.availability(event, user(1))
    assert (availability.registered_count, availability.available_spots) == (1, 1)
    assert availability.is_registered is True
    assert service.availability(event, user(2)).is_registered is False
    assert service.availability(event, None).is_registered is False


def test_register_rejects_duplicate(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events)
    service.register(user(1), event.id)
    with pytest.raises(AlreadyRegisteredError):
        service.register(user(1), event.id)


def test_register_rejects_full_event_for_next_user(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events, capacity=2)
    service.register(user(1), event.id)
    service.register(user(2), event.id)
    with pytest.raises(EventFullError):
        service.register(user(3), event.id)
    assert service.availability(event, None).available_spots == 0


def test_duplicate_is_reported_before_full(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events, capacity=1)
    service.register(user(1), event.id)
    with pytest.raises(AlreadyRegisteredError):
        service.register(user(1), event.id)


@pytest.mark.parametrize("status", [EventStatus.CANCELLED, EventStatus.FINISHED])
def test_register_rejects_non_published(
    service: RegistrationService, events: FakeEventRepository, status: EventStatus
) -> None:
    event = add_event(events, status=status)
    with pytest.raises(RegistrationClosedError):
        service.register(user(1, Role.ADMIN), event.id)


def test_register_rejects_draft_for_owner_as_conflict(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events, status=EventStatus.DRAFT)
    with pytest.raises(RegistrationClosedError):
        service.register(user(99, Role.ORGANIZER), event.id)


def test_register_hides_draft_from_attendee(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events, status=EventStatus.DRAFT)
    with pytest.raises(EventNotFoundError):
        service.register(user(1), event.id)


def test_register_missing_event(service: RegistrationService) -> None:
    with pytest.raises(EventNotFoundError):
        service.register(user(1), 404)


def test_register_rejects_ended_event(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events, days=-3)
    with pytest.raises(RegistrationClosedError):
        service.register(user(1), event.id)


def test_cancel_frees_a_spot(service: RegistrationService, events: FakeEventRepository) -> None:
    event = add_event(events, capacity=1)
    service.register(user(1), event.id)
    service.cancel(user(1), event.id)
    service.register(user(2), event.id)


def test_cancel_without_registration(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events)
    with pytest.raises(NotRegisteredError):
        service.cancel(user(1), event.id)


def test_cancel_rejected_on_finished_event(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    event = add_event(events)
    service.register(user(1), event.id)
    event.status = EventStatus.FINISHED
    with pytest.raises(RegistrationClosedError):
        service.cancel(user(1), event.id)


def test_my_events_paginated_and_ordered_by_start(
    service: RegistrationService, events: FakeEventRepository
) -> None:
    late = add_event(events, days=5)
    early = add_event(events, days=1)
    middle = add_event(events, days=3)
    for event in (late, early, middle):
        service.register(user(1), event.id)
    service.register(user(2), early.id)

    first = service.my_events(user(1), page=1, size=2)
    assert [r.event.id for r in first.items] == [early.id, middle.id]
    assert (first.total, first.pages) == (3, 2)
    second = service.my_events(user(1), page=2, size=2)
    assert [r.event.id for r in second.items] == [late.id]


def test_register_commits_once(
    service: RegistrationService, events: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    event = add_event(events)
    service.register(user(1), event.id)
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_rejected_registration_commits_nothing_and_keeps_count(
    service: RegistrationService, events: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    event = add_event(events, capacity=1)
    service.register(user(1), event.id)
    with pytest.raises(EventFullError):
        service.register(user(2), event.id)
    assert (uow.commits, uow.rollbacks) == (1, 1)
    assert events.count_registrations(event.id) == 1


def test_cancel_commits_once_and_failed_cancel_commits_nothing(
    service: RegistrationService, events: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    event = add_event(events)
    service.register(user(1), event.id)
    service.cancel(user(1), event.id)
    assert uow.commits == 2
    with pytest.raises(NotRegisteredError):
        service.cancel(user(1), event.id)
    assert uow.commits == 2


def test_reads_never_commit(
    service: RegistrationService, events: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    event = add_event(events)
    service.my_events(user(1))
    service.availability(event, user(1))
    assert uow.commits == 0
