from datetime import UTC, datetime, timedelta

import pytest

from app.application.errors import EventNotFoundError, PermissionDeniedError
from app.application.event_service import EventService
from app.domain.enums import EventStatus, Role
from app.domain.event import EventDetails, EventFilters, EventStateError, EventValidationError
from app.domain.user import UserAccount
from tests.fakes import FakeCache, FakeEventRepository, FakeEventUsageQueries, FakeUnitOfWork

NOW = datetime(2030, 1, 1, tzinfo=UTC)

OWNER = UserAccount(
    id=1, email="o@x.com", full_name="Test User", password_hash="h", role=Role.ORGANIZER
)
OTHER = UserAccount(
    id=2, email="p@x.com", full_name="Test User", password_hash="h", role=Role.ORGANIZER
)
ADMIN = UserAccount(
    id=3, email="a@x.com", full_name="Test User", password_hash="h", role=Role.ADMIN
)
ATTENDEE = UserAccount(
    id=4, email="t@x.com", full_name="Test User", password_hash="h", role=Role.ATTENDEE
)


def details(**overrides: object) -> EventDetails:
    base: dict[str, object] = {
        "name": "PyCon",
        "description": "",
        "location": "Lima",
        "start_at": NOW + timedelta(days=1),
        "end_at": NOW + timedelta(days=2),
        "capacity": 10,
    }
    base.update(overrides)
    return EventDetails(**base)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeEventRepository:
    return FakeEventRepository()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def service(repo: FakeEventRepository, uow: FakeUnitOfWork) -> EventService:
    return EventService(repo, FakeEventUsageQueries(repo), uow, FakeCache(), clock=lambda: NOW)


def test_create_starts_as_draft_and_owned_by_actor(service: EventService) -> None:
    event = service.create(OWNER, details())
    assert event.id is not None
    assert event.status is EventStatus.DRAFT
    assert event.organizer_id == OWNER.id


def test_create_rejects_attendee(service: EventService) -> None:
    with pytest.raises(PermissionDeniedError):
        service.create(ATTENDEE, details())


@pytest.mark.parametrize(
    "overrides",
    [
        {"end_at": NOW + timedelta(hours=1)},
        {"capacity": 0},
        {"start_at": NOW - timedelta(days=1), "end_at": NOW + timedelta(days=1)},
    ],
)
def test_create_validates_rules(service: EventService, overrides: dict[str, object]) -> None:
    with pytest.raises(EventValidationError):
        service.create(OWNER, details(**overrides))


def test_update_by_owner_and_admin(service: EventService) -> None:
    event = service.create(OWNER, details())
    assert service.update(OWNER, event.id, details(name="New")).name == "New"
    assert service.update(ADMIN, event.id, details(name="Admin")).name == "Admin"


def test_update_capacity_below_largest_session_conflicts(
    service: EventService, repo: FakeEventRepository
) -> None:
    event = service.create(OWNER, details(capacity=10))
    repo.max_session_capacities[event.id] = 8
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(capacity=7))
    assert service.update(OWNER, event.id, details(capacity=8)).capacity == 8


def test_update_dates_must_still_contain_sessions(
    service: EventService, repo: FakeEventRepository
) -> None:
    event = service.create(OWNER, details())
    first = NOW + timedelta(days=1, hours=2)
    last = NOW + timedelta(days=1, hours=5)
    repo.session_bounds_by_event[event.id] = (first, last)
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(start_at=first + timedelta(hours=1)))
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(end_at=last - timedelta(hours=1)))
    wider = details(start_at=first - timedelta(hours=1), end_at=last + timedelta(hours=1))
    assert service.update(OWNER, event.id, wider).start_at == wider.start_at


def test_update_capacity_below_registrations_conflicts(
    service: EventService, repo: FakeEventRepository
) -> None:
    event = service.create(OWNER, details(capacity=10))
    repo.registrations[event.id] = 5
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(capacity=4))
    assert service.update(OWNER, event.id, details(capacity=5)).capacity == 5


def test_update_by_other_organizer_denied(service: EventService) -> None:
    event = service.create(OWNER, details())
    with pytest.raises(PermissionDeniedError):
        service.update(OTHER, event.id, details(name="Hijack"))


def test_update_missing_event(service: EventService) -> None:
    with pytest.raises(EventNotFoundError):
        service.update(ADMIN, 999, details())


def test_update_allows_past_start_on_existing_event(service: EventService) -> None:
    event = service.create(OWNER, details())
    past = details(start_at=NOW - timedelta(days=2), end_at=NOW - timedelta(days=1))
    assert service.update(OWNER, event.id, past).start_at == past.start_at


@pytest.mark.parametrize("closed", [EventStatus.CANCELLED, EventStatus.FINISHED])
def test_cannot_edit_closed_event(service: EventService, closed: EventStatus) -> None:
    event = service.create(OWNER, details())
    event.status = closed
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(name="Nope"))


def test_delete_rules(service: EventService) -> None:
    event = service.create(OWNER, details())
    with pytest.raises(PermissionDeniedError):
        service.delete(OTHER, event.id)
    service.delete(OWNER, event.id)
    with pytest.raises(EventNotFoundError):
        service.get(event.id, ADMIN)


def test_draft_hidden_from_public_and_other_users(service: EventService) -> None:
    event = service.create(OWNER, details())
    for viewer in (None, OTHER, ATTENDEE):
        with pytest.raises(EventNotFoundError):
            service.get(event.id, viewer)
    assert service.get(event.id, OWNER).id == event.id
    assert service.get(event.id, ADMIN).id == event.id


def test_change_status_flow(service: EventService) -> None:
    event = service.create(OWNER, details())
    assert service.change_status(OWNER, event.id, EventStatus.PUBLISHED).status is (
        EventStatus.PUBLISHED
    )
    with pytest.raises(EventStateError):
        service.change_status(OWNER, event.id, EventStatus.DRAFT)
    with pytest.raises(PermissionDeniedError):
        service.change_status(OTHER, event.id, EventStatus.FINISHED)
    assert service.change_status(ADMIN, event.id, EventStatus.FINISHED).status is (
        EventStatus.FINISHED
    )


def test_list_visibility(service: EventService) -> None:
    pub = service.create(OWNER, details(name="Public"))
    service.change_status(OWNER, pub.id, EventStatus.PUBLISHED)
    service.create(OWNER, details(name="Secret draft"))

    def names(viewer: UserAccount | None) -> list[str]:
        return [e.name for e in service.list(viewer).items]

    assert names(None) == ["Public"]
    assert names(ATTENDEE) == ["Public"]
    assert names(OTHER) == ["Public"]
    assert sorted(names(OWNER)) == ["Public", "Secret draft"]
    assert sorted(names(ADMIN)) == ["Public", "Secret draft"]


def test_list_status_filter_and_pagination(service: EventService) -> None:
    for i in range(25):
        created = service.create(
            OWNER,
            details(
                name=f"E{i}",
                start_at=NOW + timedelta(days=i + 1),
                end_at=NOW + timedelta(days=i + 2),
            ),
        )
        service.change_status(OWNER, created.id, EventStatus.PUBLISHED)
    page = service.list(None, page=3, size=10)
    assert (page.total, page.pages, len(page.items)) == (25, 3, 5)
    first = service.list(None, page=1, size=10)
    assert [e.name for e in first.items][:2] == ["E0", "E1"]
    assert service.list(None, status=EventStatus.DRAFT).total == 0
    assert service.list(ADMIN, status=EventStatus.DRAFT).total == 0


def test_create_commits_once(service: EventService, uow: FakeUnitOfWork) -> None:
    service.create(OWNER, details())
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_rejected_create_commits_nothing_and_stores_no_event(
    service: EventService, repo: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    with pytest.raises(PermissionDeniedError):
        service.create(ATTENDEE, details())
    assert (uow.commits, uow.rollbacks) == (0, 1)
    assert repo.list_page(EventFilters(unrestricted=True), 1, 10) == ([], 0)


def test_update_runs_every_validation_then_commits_once(
    service: EventService, uow: FakeUnitOfWork
) -> None:
    event = service.create(OWNER, details())
    commits_before = uow.commits
    service.update(OWNER, event.id, details(name="Renamed"))
    assert uow.commits == commits_before + 1


def test_failed_update_leaves_stored_event_unchanged(
    service: EventService, repo: FakeEventRepository, uow: FakeUnitOfWork
) -> None:
    event = service.create(OWNER, details())
    repo.max_session_capacities[event.id] = 8
    with pytest.raises(EventStateError):
        service.update(OWNER, event.id, details(capacity=5))
    assert uow.commits == 1
    assert repo.get(event.id).capacity == 10


def test_get_and_list_never_commit(service: EventService, uow: FakeUnitOfWork) -> None:
    event = service.create(OWNER, details())
    service.get(event.id, OWNER)
    service.list(OWNER)
    assert uow.commits == 1
