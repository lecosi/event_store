from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import EventNotFoundError, SessionNotFoundError
from app.application.registration_service import RegistrationService
from app.application.session_registration_service import SessionRegistrationService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event
from app.domain.session import Session
from app.domain.session_registration import (
    AlreadyEnrolledError,
    EnrollmentClosedError,
    EventRegistrationRequiredError,
    NotEnrolledError,
    ScheduleConflictError,
    SessionFullError,
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


def user(user_id: int) -> UserAccount:
    return UserAccount(
        id=user_id,
        email=f"u{user_id}@x.com",
        full_name="Test User",
        password_hash="h",
        role=Role.ATTENDEE,
    )


class World:
    def __init__(self) -> None:
        self.events = FakeEventRepository()
        self.sessions = FakeSessionRepository()
        self.registrations = FakeRegistrationRepository(self.events)
        self.enrollments = FakeSessionRegistrationRepository(
            self.events, self.sessions, self.registrations
        )
        self.uow = FakeUnitOfWork()
        self.service = SessionRegistrationService(
            self.events, self.sessions, self.enrollments, self.uow, clock=lambda: NOW
        )
        self.event_service = RegistrationService(
            self.events, self.registrations, self.enrollments, self.uow, clock=lambda: NOW
        )

    def event(self, status: EventStatus = EventStatus.PUBLISHED) -> Event:
        return self.events.add(
            Event(
                name="PyCon",
                description="",
                location="Lima",
                start_at=NOW + timedelta(days=1),
                end_at=NOW + timedelta(days=1, hours=10),
                capacity=10,
                organizer_id=99,
                status=status,
            )
        )

    def session(
        self, event: Event, start_hours: int = 1, end_hours: int = 2, capacity: int = 1
    ) -> Session:
        return self.sessions.add(
            Session(
                event_id=event.id or 0,
                speaker_id=1,
                title="Talk",
                start_at=event.start_at + timedelta(hours=start_hours),
                end_at=event.start_at + timedelta(hours=end_hours),
                capacity=capacity,
            )
        )


@pytest.fixture
def world() -> World:
    return World()


def registered_world(
    world: World, user_id: int = 1, **event_fields: object
) -> tuple[Event, Session]:
    event = world.event()
    session = world.session(event, **event_fields)  # type: ignore[arg-type]
    world.event_service.register(user(user_id), event.id or 0)
    return event, session


def test_enroll_succeeds_for_a_registered_user(world: World) -> None:
    event, session = registered_world(world)
    result = world.service.enroll(user(1), event.id or 0, session.id or 0)
    assert (result.user_id, result.session_id) == (1, session.id)
    assert world.enrollments.is_enrolled(1, session.id or 0)


def test_enroll_rejects_the_next_user_when_the_session_is_full(world: World) -> None:
    event, session = registered_world(world)
    world.event_service.register(user(2), event.id or 0)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    with pytest.raises(SessionFullError):
        world.service.enroll(user(2), event.id or 0, session.id or 0)


def test_enroll_rejects_a_duplicate(world: World) -> None:
    event, session = registered_world(world, capacity=5)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    with pytest.raises(AlreadyEnrolledError):
        world.service.enroll(user(1), event.id or 0, session.id or 0)


def test_enroll_requires_the_event_registration(world: World) -> None:
    event = world.event()
    session = world.session(event)
    with pytest.raises(EventRegistrationRequiredError):
        world.service.enroll(user(1), event.id or 0, session.id or 0)


def test_enroll_rejects_an_overlapping_session_of_another_event(world: World) -> None:
    first_event, first = registered_world(world, start_hours=1, end_hours=3)
    second_event = world.event()
    second = world.session(second_event, start_hours=2, end_hours=4)
    world.event_service.register(user(1), second_event.id or 0)
    world.service.enroll(user(1), first_event.id or 0, first.id or 0)
    with pytest.raises(ScheduleConflictError):
        world.service.enroll(user(1), second_event.id or 0, second.id or 0)


def test_enroll_allows_every_non_overlapping_session_of_one_event(world: World) -> None:
    event = world.event()
    sessions = [world.session(event, start_hours=h, end_hours=h + 1) for h in (1, 2, 3)]
    world.event_service.register(user(1), event.id or 0)
    for session in sessions:
        world.service.enroll(user(1), event.id or 0, session.id or 0)
    assert world.enrollments.enrolled_session_ids(1, event.id or 0) == {s.id for s in sessions}


def test_enroll_rejects_a_session_of_another_event(world: World) -> None:
    event, _ = registered_world(world)
    stranger = world.session(world.event())
    with pytest.raises(SessionNotFoundError):
        world.service.enroll(user(1), event.id or 0, stranger.id or 0)


def test_enroll_hides_draft_events_from_attendees(world: World) -> None:
    event = world.event(EventStatus.DRAFT)
    session = world.session(event)
    with pytest.raises(EventNotFoundError):
        world.service.enroll(user(1), event.id or 0, session.id or 0)


def test_enroll_rejects_when_the_session_has_ended(world: World) -> None:
    event, session = registered_world(world)
    late = SessionRegistrationService(
        world.events,
        world.sessions,
        world.enrollments,
        world.uow,
        clock=lambda: session.end_at + timedelta(minutes=1),
    )
    with pytest.raises(EnrollmentClosedError):
        late.enroll(user(1), event.id or 0, session.id or 0)


def test_cancel_frees_the_seat(world: World) -> None:
    event, session = registered_world(world)
    world.event_service.register(user(2), event.id or 0)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    world.service.cancel(user(1), event.id or 0, session.id or 0)
    world.service.enroll(user(2), event.id or 0, session.id or 0)
    assert not world.enrollments.is_enrolled(1, session.id or 0)


def test_cancel_rejects_a_user_who_is_not_enrolled(world: World) -> None:
    event, session = registered_world(world)
    with pytest.raises(NotEnrolledError):
        world.service.cancel(user(1), event.id or 0, session.id or 0)


def test_cancel_is_rejected_when_the_event_is_finished(world: World) -> None:
    event, session = registered_world(world)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    event.status = EventStatus.FINISHED
    with pytest.raises(EnrollmentClosedError):
        world.service.cancel(user(1), event.id or 0, session.id or 0)


def test_cancel_unknown_event_is_not_found(world: World) -> None:
    with pytest.raises(EventNotFoundError):
        world.service.cancel(user(1), 999, 1)


def test_cancelling_the_event_registration_drops_its_session_enrollments(world: World) -> None:
    event, session = registered_world(world)
    other_event = world.event()
    other = world.session(other_event, start_hours=5, end_hours=6)
    world.event_service.register(user(1), other_event.id or 0)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    world.service.enroll(user(1), other_event.id or 0, other.id or 0)
    world.event_service.cancel(user(1), event.id or 0)
    assert not world.enrollments.is_enrolled(1, session.id or 0)
    assert world.enrollments.is_enrolled(1, other.id or 0)


def test_availability_reports_counts_spots_and_viewer_enrollment(world: World) -> None:
    event, session = registered_world(world, capacity=3)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    capacities = {session.id or 0: 3}
    mine = world.service.availability(event.id or 0, capacities, user(1))[session.id or 0]
    anonymous = world.service.availability(event.id or 0, capacities, None)[session.id or 0]
    assert (mine.enrolled_count, mine.available_spots, mine.is_enrolled) == (1, 2, True)
    assert (anonymous.enrolled_count, anonymous.available_spots, anonymous.is_enrolled) == (
        1,
        2,
        False,
    )


def test_cancelling_the_event_registration_removes_the_users_session_enrollments(
    world: World,
) -> None:
    event = world.event()
    sessions = [world.session(event, start_hours=h, end_hours=h + 1) for h in (1, 2)]
    world.event_service.register(user(1), event.id or 0)
    for session in sessions:
        world.service.enroll(user(1), event.id or 0, session.id or 0)
    world.event_service.cancel(user(1), event.id or 0)
    assert world.enrollments.enrolled_session_ids(1, event.id or 0) == set()


def test_cancelling_the_event_registration_keeps_other_users_enrollments(world: World) -> None:
    event, session = registered_world(world, capacity=5)
    world.event_service.register(user(2), event.id or 0)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    world.service.enroll(user(2), event.id or 0, session.id or 0)
    world.event_service.cancel(user(1), event.id or 0)
    assert world.enrollments.is_enrolled(2, session.id or 0)


def test_cancelling_the_event_registration_keeps_enrollments_of_other_events(
    world: World,
) -> None:
    event, session = registered_world(world)
    other_event = world.event()
    other_session = world.session(other_event, start_hours=5, end_hours=6)
    world.event_service.register(user(1), other_event.id or 0)
    world.service.enroll(user(1), event.id or 0, session.id or 0)
    world.service.enroll(user(1), other_event.id or 0, other_session.id or 0)
    world.event_service.cancel(user(1), event.id or 0)
    assert world.enrollments.is_enrolled(1, other_session.id or 0)
