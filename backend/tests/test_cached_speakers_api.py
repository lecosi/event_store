from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.application.ports import SPEAKERS_NAMESPACE
from app.infrastructure.db.models import Speaker
from tests.fakes import FakeCache
from tests.test_events_api import organizer
from tests.test_sessions_api import SPEAKERS, make_speaker


def rename_in_database(session: Session, speaker_id: int, name: str) -> None:
    row = session.exec(select(Speaker).where(Speaker.id == speaker_id)).one()
    row.name = name
    session.add(row)
    session.commit()


def test_speaker_detail_is_served_from_cache_on_second_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    speaker = make_speaker(client, organizer(client, session), name="Ada")
    first = client.get(f"{SPEAKERS}/{speaker['id']}")
    rename_in_database(session, speaker["id"], "Renamed behind the cache")
    second = client.get(f"{SPEAKERS}/{speaker['id']}")
    assert first.json()["name"] == "Ada"
    assert second.json() == first.json()


def test_speaker_list_is_served_from_cache_on_second_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    speaker = make_speaker(client, organizer(client, session), name="Ada")
    first = client.get(SPEAKERS)
    rename_in_database(session, speaker["id"], "Renamed behind the cache")
    second = client.get(SPEAKERS)
    assert second.json() == first.json()
    assert second.json()["items"][0]["name"] == "Ada"


def test_speaker_update_through_api_is_visible_on_next_detail_and_list_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    speaker = make_speaker(client, headers, name="Ada")
    client.get(f"{SPEAKERS}/{speaker['id']}")
    client.get(SPEAKERS)
    updated = client.put(
        f"{SPEAKERS}/{speaker['id']}", json={"name": "Ada L.", "bio": "bio"}, headers=headers
    )
    assert updated.status_code == 200
    assert client.get(f"{SPEAKERS}/{speaker['id']}").json()["name"] == "Ada L."
    assert client.get(SPEAKERS).json()["items"][0]["name"] == "Ada L."


def test_speaker_created_through_api_appears_in_next_cached_list(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    make_speaker(client, headers, name="Ada")
    assert client.get(SPEAKERS).json()["total"] == 1
    make_speaker(client, headers, name="Bo")
    assert client.get(SPEAKERS).json()["total"] == 2


def test_missing_speaker_answers_404_and_is_not_cached(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    assert client.get(f"{SPEAKERS}/999").status_code == 404
    assert fake_cache.sets == []
    make_speaker(client, organizer(client, session), name="Ada")
    assert client.get(f"{SPEAKERS}/1").status_code == 200


def test_list_entries_differ_per_search_text_and_page(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    make_speaker(client, headers, name="Ada")
    make_speaker(client, headers, name="Bo")
    assert client.get(SPEAKERS, params={"q": "ada"}).json()["total"] == 1
    assert client.get(SPEAKERS, params={"q": "bo"}).json()["total"] == 1
    assert client.get(SPEAKERS, params={"size": 1, "page": 2}).json()["items"][0]["name"] == "Bo"
    assert len({key for _, key, _, _ in fake_cache.sets}) == 3


def test_cache_keys_never_contain_raw_search_text(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    client.get(SPEAKERS, params={"q": "secret-term:../*"})
    assert fake_cache.sets
    assert all("secret-term" not in key for _, key, _, _ in fake_cache.sets)


def test_entries_use_the_configured_speaker_ttl(
    client: TestClient,
    session: Session,
    fake_cache: FakeCache,
    override_settings: Callable[..., None],
) -> None:
    override_settings(cache_ttl_speakers_seconds=7)
    speaker = make_speaker(client, organizer(client, session))
    client.get(SPEAKERS)
    client.get(f"{SPEAKERS}/{speaker['id']}")
    assert {ns for ns, _, _, _ in fake_cache.sets} == {SPEAKERS_NAMESPACE}
    assert [ttl for _, _, _, ttl in fake_cache.sets] == [7, 7]


def test_speaker_reads_answer_from_database_when_redis_is_down(
    client: TestClient, session: Session, unreachable_cache: object
) -> None:
    headers = organizer(client, session)
    speaker = make_speaker(client, headers, name="Ada")
    assert client.get(f"{SPEAKERS}/{speaker['id']}").json()["name"] == "Ada"
    assert client.get(SPEAKERS).json()["total"] == 1
    assert client.get(f"{SPEAKERS}/999").status_code == 404
