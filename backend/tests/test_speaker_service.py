import pytest

from app.application.errors import (
    PermissionDeniedError,
    SpeakerEmailTakenError,
    SpeakerInUseError,
    SpeakerNotFoundError,
)
from app.application.speaker_service import SpeakerService
from app.domain.enums import Role
from app.domain.session import Session
from app.domain.speaker import SpeakerDetails
from app.domain.user import UserAccount
from tests.fakes import FakeSessionRepository, FakeSpeakerRepository
from tests.test_session_service import BASE, at

ORGANIZER = UserAccount(id=1, email="o@x.com", password_hash="h", role=Role.ORGANIZER)
ADMIN = UserAccount(id=3, email="a@x.com", password_hash="h", role=Role.ADMIN)
ATTENDEE = UserAccount(id=4, email="t@x.com", password_hash="h", role=Role.ATTENDEE)


def details(**overrides: object) -> SpeakerDetails:
    base: dict[str, object] = {"name": "Ada", "bio": "Pioneer", "email": "ada@x.com"}
    base.update(overrides)
    return SpeakerDetails(**base)  # type: ignore[arg-type]


@pytest.fixture
def sessions() -> FakeSessionRepository:
    return FakeSessionRepository()


@pytest.fixture
def service(sessions: FakeSessionRepository) -> SpeakerService:
    return SpeakerService(FakeSpeakerRepository(sessions))


def test_organizer_and_admin_can_create_attendee_cannot(service: SpeakerService) -> None:
    assert service.create(ORGANIZER, details()).id is not None
    assert service.create(ADMIN, details(email="b@x.com")).id is not None
    with pytest.raises(PermissionDeniedError):
        service.create(ATTENDEE, details(email="c@x.com"))


def test_email_must_be_unique_only_when_provided(service: SpeakerService) -> None:
    service.create(ORGANIZER, details())
    with pytest.raises(SpeakerEmailTakenError):
        service.create(ORGANIZER, details(email="ADA@x.com"))
    service.create(ORGANIZER, details(email=None))
    service.create(ORGANIZER, details(email=None))


def test_update_keeps_own_email_but_rejects_taken_one(service: SpeakerService) -> None:
    first = service.create(ORGANIZER, details())
    second = service.create(ORGANIZER, details(email="b@x.com"))
    assert service.update(ORGANIZER, first.id, details(name="Ada L.")).name == "Ada L."
    with pytest.raises(SpeakerEmailTakenError):
        service.update(ORGANIZER, second.id, details(email="ada@x.com"))


def test_get_list_and_not_found(service: SpeakerService) -> None:
    created = service.create(ORGANIZER, details())
    assert service.get(created.id).name == "Ada"
    assert [s.id for s in service.list_page().items] == [created.id]
    with pytest.raises(SpeakerNotFoundError):
        service.get(999)
    with pytest.raises(SpeakerNotFoundError):
        service.update(ORGANIZER, 999, details())


def test_delete_requires_role_and_blocks_when_speaker_has_sessions(
    service: SpeakerService, sessions: FakeSessionRepository
) -> None:
    created = service.create(ORGANIZER, details())
    sessions.add(
        Session(
            event_id=1, speaker_id=created.id, title="T", start_at=BASE, end_at=at(1), capacity=1
        )
    )
    with pytest.raises(PermissionDeniedError):
        service.delete(ATTENDEE, created.id)
    with pytest.raises(SpeakerInUseError):
        service.delete(ORGANIZER, created.id)


def test_delete_free_speaker(service: SpeakerService) -> None:
    created = service.create(ORGANIZER, details())
    service.delete(ORGANIZER, created.id)
    with pytest.raises(SpeakerNotFoundError):
        service.get(created.id)


def test_list_page_trims_search_and_computes_pages(service: SpeakerService) -> None:
    for index, name in enumerate(["Ada", "Alan", "Grace"]):
        service.create(ORGANIZER, details(name=name, email=f"{index}@x.com"))
    page = service.list_page(q="  a ", page=1, size=2)
    assert [s.name for s in page.items] == ["Ada", "Alan"]
    assert (page.total, page.pages) == (3, 2)
    assert service.list_page(q="   ").total == 3
