from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import EventNotFoundError
from app.application.session_catalogue import SessionCatalogue, SessionView
from app.domain.enums import EventStatus, Role
from app.domain.event import Event
from app.domain.session import Session, SessionWithSpeaker
from app.domain.user import UserAccount
from tests.fakes import (
    FakeEventRepository,
    FakeRegistrationRepository,
    FakeSessionRegistrationRepository,
    FakeSessionRepository,
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


class StubEvents:
    def __init__(self, visible: bool) -> None:
        self._visible = visible

    def get(self, event_id: int, viewer: UserAccount | None) -> Event:
        if not self._visible:
            raise EventNotFoundError(event_id)
        return Event(
            id=event_id,
            name="PyCon",
            description="",
            location="Lima",
            start_at=NOW,
            end_at=NOW + timedelta(hours=10),
            capacity=10,
            organizer_id=99,
            status=EventStatus.PUBLISHED,
        )


class StubSchedule:
    def __init__(self, items: list[SessionWithSpeaker]) -> None:
        self.items = items

    def list_for_event(self, event_id: int) -> list[SessionWithSpeaker]:
        return self.items


def scheduled(session: Session, speaker_name: str = "Grace") -> SessionWithSpeaker:
    return SessionWithSpeaker(session=session, speaker_name=speaker_name)


def new_session(capacity: int, event_id: int = 1) -> Session:
    return Session(
        event_id=event_id,
        speaker_id=1,
        title="Talk",
        start_at=NOW,
        end_at=NOW + timedelta(hours=1),
        capacity=capacity,
    )


class World:
    def __init__(self) -> None:
        events = FakeEventRepository()
        self.sessions = FakeSessionRepository()
        self.enrollments = FakeSessionRegistrationRepository(
            events, self.sessions, FakeRegistrationRepository(events)
        )

    def catalogue(self, items: list[SessionWithSpeaker], visible: bool = True) -> SessionCatalogue:
        return SessionCatalogue(StubEvents(visible), StubSchedule(items), self.enrollments)


@pytest.fixture
def world() -> World:
    return World()


def test_listing_reports_counts_spots_and_viewer_enrollment(world: World) -> None:
    session = world.sessions.add(new_session(capacity=3))
    world.enrollments.add(1, session.id or 0)
    catalogue = world.catalogue([scheduled(session)])
    mine = catalogue.list_for_event(1, user(1))[0].availability
    anonymous = catalogue.list_for_event(1, None)[0].availability
    assert (mine.enrolled_count, mine.available_spots, mine.is_enrolled) == (1, 2, True)
    assert (anonymous.enrolled_count, anonymous.available_spots, anonymous.is_enrolled) == (
        1,
        2,
        False,
    )


def test_listing_a_hidden_event_raises_not_found(world: World) -> None:
    session = world.sessions.add(new_session(capacity=3))
    catalogue = world.catalogue([scheduled(session)], visible=False)
    with pytest.raises(EventNotFoundError):
        catalogue.list_for_event(1, None)


def test_availability_of_a_full_session_has_no_spots_left(world: World) -> None:
    session = world.sessions.add(new_session(capacity=1))
    world.enrollments.add(1, session.id or 0)
    (view,) = world.catalogue([]).with_availability(1, [scheduled(session)], user(2))
    assert (view.availability.available_spots, view.availability.is_enrolled) == (0, False)


def test_unenrolled_view_offers_every_seat() -> None:
    session = new_session(capacity=5)
    session.id = 7
    view = SessionView.unenrolled(scheduled(session))
    assert (view.availability.enrolled_count, view.availability.available_spots) == (0, 5)
    assert view.availability.is_enrolled is False
