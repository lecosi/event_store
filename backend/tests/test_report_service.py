from datetime import UTC, date, datetime, timedelta

import pytest

from app.application.cache_policy import EventCache
from app.application.errors import EventNotFoundError, PermissionDeniedError
from app.application.event_service import EventService
from app.application.report_service import ParticipantParams, ReportService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventValidationError
from app.domain.registration import ParticipantRow
from app.domain.user import UserAccount
from tests.fakes import (
    FakeCache,
    FakeEventRepository,
    FakeEventUsageQueries,
    FakeRegistrationRepository,
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
        self.users = FakeUserRepository()
        self.registrations = FakeRegistrationRepository(self.events, self.users)
        self.service = ReportService(
            EventService(
                self.events,
                FakeEventUsageQueries(self.events),
                FakeUnitOfWork(),
                EventCache(FakeCache(), 60),
            ),
            self.registrations,
        )

    def event(self, name: str, organizer_id: int, days: int = 1, **fields: object) -> Event:
        return self.events.add(
            Event(
                name=name,
                description="",
                location="Lima",
                start_at=NOW + timedelta(days=days),
                end_at=NOW + timedelta(days=days, hours=5),
                capacity=10,
                organizer_id=organizer_id,
                **fields,  # type: ignore[arg-type]
            )
        )

    def attendee(self, event: Event, full_name: str) -> None:
        user = self.users.add(
            UserAccount(
                email=f"{full_name.lower().replace(' ', '.')}@x.com",
                full_name=full_name,
                password_hash="h",
            )
        )
        assert user.id is not None and event.id is not None
        self.registrations.register(user.id, event.id, lambda *_: None)


@pytest.fixture
def scenario() -> Scenario:
    return Scenario()


def names(rows: list[ParticipantRow]) -> list[str]:
    return [row.full_name for row in rows]


def test_organizer_report_only_contains_own_events(scenario: Scenario) -> None:
    mine = scenario.event("Mine", OWNER.id)  # type: ignore[arg-type]
    theirs = scenario.event("Theirs", OTHER.id)  # type: ignore[arg-type]
    scenario.attendee(mine, "Ana Gomez")
    scenario.attendee(theirs, "Luis Perez")

    page = scenario.service.participants(OWNER, ParticipantParams(), 1, 10)

    assert names(page.items) == ["Ana Gomez"]
    assert page.total == 1


def test_admin_report_contains_every_event(scenario: Scenario) -> None:
    scenario.attendee(scenario.event("Mine", 1, days=1), "Ana Gomez")
    scenario.attendee(scenario.event("Theirs", 2, days=2), "Luis Perez")

    page = scenario.service.participants(ADMIN, ParticipantParams(), 1, 10)

    assert names(page.items) == ["Ana Gomez", "Luis Perez"]


def test_attendee_cannot_request_the_report(scenario: Scenario) -> None:
    with pytest.raises(PermissionDeniedError):
        scenario.service.participants(ATTENDEE, ParticipantParams(), 1, 10)
    with pytest.raises(PermissionDeniedError):
        scenario.service.iter_participants(ATTENDEE, ParticipantParams())


def test_organizer_cannot_filter_by_a_foreign_event(scenario: Scenario) -> None:
    foreign = scenario.event("Theirs", 2)

    with pytest.raises(PermissionDeniedError):
        scenario.service.participants(OWNER, ParticipantParams(event_id=foreign.id), 1, 10)
    with pytest.raises(PermissionDeniedError):
        scenario.service.iter_participants(OWNER, ParticipantParams(event_id=foreign.id))


def test_unknown_event_is_not_found(scenario: Scenario) -> None:
    with pytest.raises(EventNotFoundError):
        scenario.service.participants(ADMIN, ParticipantParams(event_id=99), 1, 10)


def test_admin_can_filter_by_any_event(scenario: Scenario) -> None:
    foreign = scenario.event("Theirs", 2)
    scenario.attendee(foreign, "Luis Perez")

    page = scenario.service.participants(ADMIN, ParticipantParams(event_id=foreign.id), 1, 10)

    assert names(page.items) == ["Luis Perez"]


def test_blank_query_is_ignored_and_text_is_trimmed(scenario: Scenario) -> None:
    scenario.attendee(scenario.event("PyCon", 1), "Ana Gomez")
    scenario.attendee(scenario.event("JSConf", 1, days=2), "Luis Perez")

    blank = scenario.service.participants(OWNER, ParticipantParams(q="   "), 1, 10)
    trimmed = scenario.service.participants(OWNER, ParticipantParams(q="  pycon "), 1, 10)

    assert blank.total == 2
    assert names(trimmed.items) == ["Ana Gomez"]


def test_status_filter(scenario: Scenario) -> None:
    scenario.attendee(scenario.event("Draft", 1), "Ana Gomez")
    scenario.attendee(scenario.event("Live", 1, days=2, status=EventStatus.PUBLISHED), "Luis Perez")

    page = scenario.service.participants(
        OWNER, ParticipantParams(status=EventStatus.PUBLISHED), 1, 10
    )

    assert names(page.items) == ["Luis Perez"]


def test_date_range_is_inclusive_on_whole_utc_days(scenario: Scenario) -> None:
    first = scenario.event("First", 1, days=1)
    last = scenario.event("Last", 1, days=3)
    first.start_at = datetime(2030, 1, 2, 0, 0, 0, tzinfo=UTC)
    last.start_at = datetime(2030, 1, 4, 23, 59, 59, tzinfo=UTC)
    scenario.attendee(first, "Ana Gomez")
    scenario.attendee(last, "Luis Perez")

    inclusive = scenario.service.participants(
        OWNER, ParticipantParams(date_from=date(2030, 1, 2), date_to=date(2030, 1, 4)), 1, 10
    )
    only_first_day = scenario.service.participants(
        OWNER, ParticipantParams(date_to=date(2030, 1, 3)), 1, 10
    )
    after_first_day = scenario.service.participants(
        OWNER, ParticipantParams(date_from=date(2030, 1, 3)), 1, 10
    )

    assert names(inclusive.items) == ["Ana Gomez", "Luis Perez"]
    assert names(only_first_day.items) == ["Ana Gomez"]
    assert names(after_first_day.items) == ["Luis Perez"]


def test_date_to_before_date_from_is_rejected(scenario: Scenario) -> None:
    params = ParticipantParams(date_from=date(2030, 1, 5), date_to=date(2030, 1, 4))

    with pytest.raises(EventValidationError):
        scenario.service.participants(OWNER, params, 1, 10)
    with pytest.raises(EventValidationError):
        scenario.service.iter_participants(OWNER, params)


def test_pagination_reports_total_and_pages(scenario: Scenario) -> None:
    event = scenario.event("PyCon", 1)
    for n in range(5):
        scenario.attendee(event, f"Person {n}")

    page = scenario.service.participants(OWNER, ParticipantParams(), 2, 2)

    assert names(page.items) == ["Person 2", "Person 3"]
    assert (page.total, page.page, page.size, page.pages) == (5, 2, 2, 3)


def test_empty_report_has_zero_pages(scenario: Scenario) -> None:
    page = scenario.service.participants(OWNER, ParticipantParams(), 1, 10)

    assert (page.items, page.total, page.pages) == ([], 0, 0)


def test_iteration_yields_the_same_rows_as_the_page(scenario: Scenario) -> None:
    event = scenario.event("PyCon", 1)
    for n in range(3):
        scenario.attendee(event, f"Person {n}")

    streamed = list(scenario.service.iter_participants(OWNER, ParticipantParams()))
    paged = scenario.service.participants(OWNER, ParticipantParams(), 1, 10).items

    assert streamed == paged
