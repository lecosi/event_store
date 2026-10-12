from datetime import UTC, date, datetime, timedelta

import pytest

from app.application.cache_policy import EventCache
from app.application.errors import (
    EventNotFoundError,
    PermissionDeniedError,
    SessionNotFoundError,
)
from app.application.event_service import EventService
from app.application.report_service import SessionParticipantParams, SessionReportService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventValidationError
from app.domain.session import Session
from app.domain.session_registration import SessionParticipantRow
from app.domain.user import UserAccount
from tests.fakes import (
    FakeCache,
    FakeEventRepository,
    FakeEventUsageQueries,
    FakeRegistrationRepository,
    FakeSessionRegistrationRepository,
    FakeSessionRepository,
    FakeUnitOfWork,
    FakeUserRepository,
)

NOW = datetime(2030, 1, 1, tzinfo=UTC)

OWNER = UserAccount(
    id=1, email="o@x.com", full_name="Owner", password_hash="h", role=Role.ORGANIZER
)
OTHER = UserAccount(
    id=2, email="p@x.com", full_name="Other", password_hash="h", role=Role.ORGANIZER
)
ADMIN = UserAccount(id=3, email="a@x.com", full_name="Admin", password_hash="h", role=Role.ADMIN)
ATTENDEE = UserAccount(
    id=4, email="t@x.com", full_name="Attendee", password_hash="h", role=Role.ATTENDEE
)


class Scenario:
    def __init__(self) -> None:
        self.events = FakeEventRepository()
        self.sessions = FakeSessionRepository()
        self.users = FakeUserRepository()
        registrations = FakeRegistrationRepository(self.events, self.users)
        self.enrollments = FakeSessionRegistrationRepository(
            self.events, self.sessions, registrations, self.users
        )
        self.service = SessionReportService(
            EventService(
                self.events,
                FakeEventUsageQueries(self.events),
                FakeUnitOfWork(),
                EventCache(FakeCache(), 60),
            ),
            self.sessions,
            self.enrollments,
        )

    def event(self, name: str, organizer_id: int, **fields: object) -> Event:
        return self.events.add(
            Event(
                name=name,
                description="",
                location="Lima",
                start_at=NOW + timedelta(days=1),
                end_at=NOW + timedelta(days=5),
                capacity=10,
                organizer_id=organizer_id,
                **fields,  # type: ignore[arg-type]
            )
        )

    def session(self, event: Event, title: str, days: int = 1) -> Session:
        return self.sessions.add(
            Session(
                event_id=event.id or 0,
                speaker_id=1,
                title=title,
                start_at=NOW + timedelta(days=days),
                end_at=NOW + timedelta(days=days, hours=1),
                capacity=10,
            )
        )

    def enroll(self, session: Session, full_name: str) -> None:
        user = self.users.add(
            UserAccount(
                email=f"{full_name.lower().replace(' ', '.')}@x.com",
                full_name=full_name,
                password_hash="h",
            )
        )
        assert user.id is not None and session.id is not None
        self.enrollments.add(user.id, session.id)


@pytest.fixture
def scenario() -> Scenario:
    return Scenario()


def names(rows: list[SessionParticipantRow]) -> list[str]:
    return [row.full_name for row in rows]


def test_row_carries_person_event_session_and_session_start(scenario: Scenario) -> None:
    session = scenario.session(scenario.event("PyCon", 1), "Keynote", days=2)
    scenario.enroll(session, "Ana Gomez")

    page = scenario.service.participants(OWNER, SessionParticipantParams(), 1, 10)

    assert page.items == [
        SessionParticipantRow(
            "Ana Gomez", "ana.gomez@x.com", "PyCon", "Keynote", NOW + timedelta(days=2)
        )
    ]


def test_organizer_report_only_contains_sessions_of_own_events(scenario: Scenario) -> None:
    scenario.enroll(scenario.session(scenario.event("Mine", 1), "Keynote"), "Ana Gomez")
    scenario.enroll(scenario.session(scenario.event("Theirs", 2), "Keynote"), "Luis Perez")

    page = scenario.service.participants(OWNER, SessionParticipantParams(), 1, 10)

    assert names(page.items) == ["Ana Gomez"]
    assert page.total == 1


def test_admin_report_contains_every_event(scenario: Scenario) -> None:
    scenario.enroll(scenario.session(scenario.event("Mine", 1), "Keynote"), "Ana Gomez")
    scenario.enroll(scenario.session(scenario.event("Theirs", 2), "Keynote", 2), "Luis Perez")

    page = scenario.service.participants(ADMIN, SessionParticipantParams(), 1, 10)

    assert names(page.items) == ["Ana Gomez", "Luis Perez"]


def test_attendee_cannot_request_the_report(scenario: Scenario) -> None:
    with pytest.raises(PermissionDeniedError):
        scenario.service.participants(ATTENDEE, SessionParticipantParams(), 1, 10)
    with pytest.raises(PermissionDeniedError):
        scenario.service.iter_participants(ATTENDEE, SessionParticipantParams())


def test_organizer_cannot_filter_by_a_foreign_event(scenario: Scenario) -> None:
    foreign = scenario.event("Theirs", 2)

    with pytest.raises(PermissionDeniedError):
        scenario.service.participants(OWNER, SessionParticipantParams(event_id=foreign.id), 1, 10)


def test_organizer_cannot_filter_by_a_foreign_session(scenario: Scenario) -> None:
    foreign = scenario.session(scenario.event("Theirs", 2), "Keynote")

    with pytest.raises(PermissionDeniedError):
        scenario.service.participants(OWNER, SessionParticipantParams(session_id=foreign.id), 1, 10)
    with pytest.raises(PermissionDeniedError):
        scenario.service.iter_participants(OWNER, SessionParticipantParams(session_id=foreign.id))


def test_unknown_event_is_not_found(scenario: Scenario) -> None:
    with pytest.raises(EventNotFoundError):
        scenario.service.participants(ADMIN, SessionParticipantParams(event_id=99), 1, 10)


def test_unknown_session_is_not_found(scenario: Scenario) -> None:
    with pytest.raises(SessionNotFoundError):
        scenario.service.participants(ADMIN, SessionParticipantParams(session_id=99), 1, 10)


def test_session_filter_limits_the_report_to_that_session(scenario: Scenario) -> None:
    event = scenario.event("PyCon", 1)
    keynote = scenario.session(event, "Keynote", 1)
    workshop = scenario.session(event, "Workshop", 2)
    scenario.enroll(keynote, "Ana Gomez")
    scenario.enroll(workshop, "Luis Perez")

    page = scenario.service.participants(
        OWNER, SessionParticipantParams(session_id=workshop.id), 1, 10
    )

    assert names(page.items) == ["Luis Perez"]


def test_admin_can_filter_by_any_session(scenario: Scenario) -> None:
    foreign = scenario.session(scenario.event("Theirs", 2), "Keynote")
    scenario.enroll(foreign, "Luis Perez")

    page = scenario.service.participants(
        ADMIN, SessionParticipantParams(session_id=foreign.id), 1, 10
    )

    assert names(page.items) == ["Luis Perez"]


def test_text_filter_matches_session_title_or_event_name_and_is_trimmed(
    scenario: Scenario,
) -> None:
    scenario.enroll(scenario.session(scenario.event("PyCon", 1), "Keynote", 1), "Ana Gomez")
    scenario.enroll(scenario.session(scenario.event("JSConf", 1), "Python intro", 2), "Luis Perez")
    scenario.enroll(scenario.session(scenario.event("Other", 1), "Talk", 3), "Eva Ruiz")

    blank = scenario.service.participants(OWNER, SessionParticipantParams(q="   "), 1, 10)
    by_event = scenario.service.participants(OWNER, SessionParticipantParams(q=" pycon "), 1, 10)
    by_title = scenario.service.participants(OWNER, SessionParticipantParams(q="INTRO"), 1, 10)

    assert blank.total == 3
    assert names(by_event.items) == ["Ana Gomez"]
    assert names(by_title.items) == ["Luis Perez"]


def test_status_filter_uses_the_event_status(scenario: Scenario) -> None:
    scenario.enroll(scenario.session(scenario.event("Draft", 1), "Keynote", 1), "Ana Gomez")
    live = scenario.event("Live", 1, status=EventStatus.PUBLISHED)
    scenario.enroll(scenario.session(live, "Keynote", 2), "Luis Perez")

    page = scenario.service.participants(
        OWNER, SessionParticipantParams(status=EventStatus.PUBLISHED), 1, 10
    )

    assert names(page.items) == ["Luis Perez"]


def test_date_range_applies_to_the_session_start_on_whole_utc_days(scenario: Scenario) -> None:
    event = scenario.event("PyCon", 1)
    first = scenario.session(event, "First", 1)
    last = scenario.session(event, "Last", 3)
    first.start_at = datetime(2030, 1, 2, 0, 0, 0, tzinfo=UTC)
    last.start_at = datetime(2030, 1, 4, 23, 59, 59, tzinfo=UTC)
    scenario.enroll(first, "Ana Gomez")
    scenario.enroll(last, "Luis Perez")

    inclusive = scenario.service.participants(
        OWNER,
        SessionParticipantParams(date_from=date(2030, 1, 2), date_to=date(2030, 1, 4)),
        1,
        10,
    )
    only_first_day = scenario.service.participants(
        OWNER, SessionParticipantParams(date_to=date(2030, 1, 3)), 1, 10
    )
    after_first_day = scenario.service.participants(
        OWNER, SessionParticipantParams(date_from=date(2030, 1, 3)), 1, 10
    )

    assert names(inclusive.items) == ["Ana Gomez", "Luis Perez"]
    assert names(only_first_day.items) == ["Ana Gomez"]
    assert names(after_first_day.items) == ["Luis Perez"]


def test_date_to_before_date_from_is_rejected(scenario: Scenario) -> None:
    params = SessionParticipantParams(date_from=date(2030, 1, 5), date_to=date(2030, 1, 4))

    with pytest.raises(EventValidationError):
        scenario.service.participants(OWNER, params, 1, 10)
    with pytest.raises(EventValidationError):
        scenario.service.iter_participants(OWNER, params)


def test_pagination_reports_total_and_pages(scenario: Scenario) -> None:
    session = scenario.session(scenario.event("PyCon", 1), "Keynote")
    for n in range(5):
        scenario.enroll(session, f"Person {n}")

    page = scenario.service.participants(OWNER, SessionParticipantParams(), 2, 2)

    assert names(page.items) == ["Person 2", "Person 3"]
    assert (page.total, page.page, page.size, page.pages) == (5, 2, 2, 3)


def test_empty_report_has_zero_pages(scenario: Scenario) -> None:
    page = scenario.service.participants(OWNER, SessionParticipantParams(), 1, 10)

    assert (page.items, page.total, page.pages) == ([], 0, 0)


def test_iteration_yields_the_same_rows_as_the_page(scenario: Scenario) -> None:
    session = scenario.session(scenario.event("PyCon", 1), "Keynote")
    for n in range(3):
        scenario.enroll(session, f"Person {n}")

    streamed = list(scenario.service.iter_participants(OWNER, SessionParticipantParams()))
    paged = scenario.service.participants(OWNER, SessionParticipantParams(), 1, 10).items

    assert streamed == paged
