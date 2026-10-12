from datetime import UTC, datetime, timedelta

import pytest

from app.application.close_past_events import close_past_events
from app.application.ports import EVENTS_NAMESPACE, SESSIONS_NAMESPACE
from app.domain.enums import EventStatus
from app.domain.event import Event
from app.domain.session import Session
from app.infrastructure.cache.null_cache import NullCache
from tests.fakes import (
    FakeCache,
    FakeEventRepository,
    FakeRegistrationRepository,
    FakeSessionRegistrationRepository,
    FakeSessionRepository,
    FakeUnitOfWork,
)

NOW = datetime(2030, 6, 1, 12, tzinfo=UTC)


class Env:
    def __init__(self) -> None:
        self.events = FakeEventRepository()
        self.uow = FakeUnitOfWork()
        self.cache = FakeCache()

    def event(self, status: EventStatus, ends_in: timedelta, name: str = "PyCon") -> Event:
        end = NOW + ends_in
        return self.events.add(
            Event(
                name=name,
                description="",
                location="Lima",
                start_at=end - timedelta(hours=5),
                end_at=end,
                capacity=10,
                organizer_id=1,
                status=status,
            )
        )

    def close(self) -> int:
        return close_past_events(self.events, self.uow, self.cache, clock=lambda: NOW)

    def status_of(self, event: Event) -> EventStatus:
        stored = self.events.get(event.id or 0)
        assert stored is not None
        return stored.status


@pytest.fixture
def env() -> Env:
    return Env()


def test_published_event_that_already_ended_is_finished(env: Env) -> None:
    event = env.event(EventStatus.PUBLISHED, timedelta(hours=-1))

    assert env.close() == 1
    assert env.status_of(event) is EventStatus.FINISHED


def test_published_event_still_in_progress_is_left_published(env: Env) -> None:
    event = env.event(EventStatus.PUBLISHED, timedelta(hours=1))

    assert env.close() == 0
    assert env.status_of(event) is EventStatus.PUBLISHED


def test_event_ending_exactly_now_is_still_in_progress(env: Env) -> None:
    event = env.event(EventStatus.PUBLISHED, timedelta(0))

    assert env.close() == 0
    assert env.status_of(event) is EventStatus.PUBLISHED


@pytest.mark.parametrize("status", [EventStatus.DRAFT, EventStatus.CANCELLED, EventStatus.FINISHED])
def test_past_events_in_other_statuses_are_untouched(env: Env, status: EventStatus) -> None:
    event = env.event(status, timedelta(days=-3))

    assert env.close() == 0
    assert env.status_of(event) is status


def test_only_the_published_past_events_are_counted_and_finished(env: Env) -> None:
    past = [env.event(EventStatus.PUBLISHED, timedelta(days=-n), f"Past {n}") for n in (1, 2, 3)]
    env.event(EventStatus.PUBLISHED, timedelta(days=1), "Upcoming")
    env.event(EventStatus.DRAFT, timedelta(days=-1), "Draft")

    assert env.close() == 3
    assert {env.status_of(event) for event in past} == {EventStatus.FINISHED}


def test_running_twice_closes_nothing_the_second_time(env: Env) -> None:
    env.event(EventStatus.PUBLISHED, timedelta(hours=-1))

    assert env.close() == 1
    assert env.close() == 0


def test_closing_commits_once_for_the_whole_batch(env: Env) -> None:
    env.event(EventStatus.PUBLISHED, timedelta(days=-1), "One")
    env.event(EventStatus.PUBLISHED, timedelta(days=-2), "Two")

    env.close()

    assert env.uow.commits == 1


def test_events_and_sessions_caches_are_invalidated_after_closing(env: Env) -> None:
    env.event(EventStatus.PUBLISHED, timedelta(hours=-1))

    env.close()

    assert env.cache.invalidations == [EVENTS_NAMESPACE, SESSIONS_NAMESPACE]


def test_caches_are_left_alone_when_nothing_was_closed(env: Env) -> None:
    env.event(EventStatus.PUBLISHED, timedelta(hours=1))

    env.close()

    assert env.cache.invalidations == []


def test_registrations_and_session_enrollments_are_kept(env: Env) -> None:
    event = env.event(EventStatus.PUBLISHED, timedelta(hours=-1))
    sessions = FakeSessionRepository()
    registrations = FakeRegistrationRepository(env.events)
    enrollments = FakeSessionRegistrationRepository(env.events, sessions, registrations)
    session = sessions.add(
        Session(
            event_id=event.id or 0,
            speaker_id=1,
            title="Keynote",
            start_at=event.start_at,
            end_at=event.start_at + timedelta(hours=1),
            capacity=5,
        )
    )
    registrations.register(7, event.id or 0, lambda *_: None)
    enrollments.enroll(7, session.id or 0, lambda *_: None)

    env.close()

    assert registrations.is_registered(7, event.id or 0)
    assert enrollments.is_enrolled(7, session.id or 0)


def test_works_with_a_null_cache(env: Env) -> None:
    env.event(EventStatus.PUBLISHED, timedelta(hours=-1))

    assert close_past_events(env.events, env.uow, NullCache(), clock=lambda: NOW) == 1
