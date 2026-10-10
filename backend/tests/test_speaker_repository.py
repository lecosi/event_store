import pytest
from sqlmodel import Session

from app.application.errors import SpeakerEmailTakenError
from app.domain.speaker import Speaker
from app.infrastructure.db.models import Speaker as SpeakerRow
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository


def test_absent_email_is_stored_as_null_and_may_repeat(session: Session) -> None:
    repo = SqlSpeakerRepository(session)
    first = repo.add(Speaker(name="A", bio="", email=None))
    repo.add(Speaker(name="B", bio="", email=None))

    row = session.get(SpeakerRow, first.id)
    assert row is not None
    assert row.email is None
    assert first.email is None


def test_duplicate_email_on_add_maps_to_domain_error(session: Session) -> None:
    repo = SqlSpeakerRepository(session)
    repo.add(Speaker(name="A", bio="", email="a@x.com"))
    with pytest.raises(SpeakerEmailTakenError):
        repo.add(Speaker(name="B", bio="", email="a@x.com"))
    assert repo.add(Speaker(name="C", bio="", email="c@x.com")).id is not None


def test_duplicate_email_on_update_maps_to_domain_error(session: Session) -> None:
    repo = SqlSpeakerRepository(session)
    repo.add(Speaker(name="A", bio="", email="a@x.com"))
    other = repo.add(Speaker(name="B", bio="", email="b@x.com"))
    other.email = "a@x.com"
    with pytest.raises(SpeakerEmailTakenError):
        repo.update(other)


def test_list_page_filters_orders_and_paginates(session: Session) -> None:
    repo = SqlSpeakerRepository(session)
    for name in ["Beta", "Alpha Two", "Alpha One", "Gamma"]:
        repo.add(Speaker(name=name, bio="", email=None))

    items, total = repo.list_page(None, page=1, size=3)
    assert [s.name for s in items] == ["Alpha One", "Alpha Two", "Beta"]
    assert total == 4
    items, total = repo.list_page("ALPHA", page=1, size=10)
    assert sorted(s.name for s in items) == ["Alpha One", "Alpha Two"]
    assert total == 2
    items, _ = repo.list_page("alpha", page=2, size=1)
    assert len(items) == 1
