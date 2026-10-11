from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.application.ports import SESSIONS_NAMESPACE
from app.infrastructure.db.models import Session as SessionRow
from tests.fakes import FakeCache
from tests.test_events_api import organizer, publish
from tests.test_sessions_api import SPEAKERS, make_event, make_speaker, session_body, url


def titles(response_json: list[dict]) -> list[str]:
    return [item["title"] for item in response_json]


def retitle_in_database(session: Session, session_id: int, title: str) -> None:
    row = session.exec(select(SessionRow).where(SessionRow.id == session_id)).one()
    row.title = title
    session.add(row)
    session.commit()


def event_with_session(
    client: TestClient, headers: dict[str, str], published: bool = True, **session_fields: object
) -> tuple[dict, dict, dict]:
    event = make_event(client, headers)
    if published:
        publish(client, headers, event["id"])
    speaker = make_speaker(client, headers)
    created = client.post(
        url(event["id"]), json=session_body(speaker["id"], **session_fields), headers=headers
    )
    assert created.status_code == 201, created.text
    return event, speaker, created.json()


def test_sessions_are_served_from_cache_on_second_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    event, _, created = event_with_session(client, organizer(client, session))
    first = client.get(url(event["id"]))
    retitle_in_database(session, created["id"], "Renamed behind the cache")
    second = client.get(url(event["id"]))
    assert titles(first.json()) == ["Keynote"]
    assert second.json() == first.json()


def test_session_write_through_api_is_visible_on_next_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event, speaker, created = event_with_session(client, headers)
    assert titles(client.get(url(event["id"])).json()) == ["Keynote"]
    updated = client.put(
        url(event["id"], created["id"]),
        json=session_body(speaker["id"], title="Closing"),
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert titles(client.get(url(event["id"])).json()) == ["Closing"]


def test_speaker_update_changes_speaker_name_in_next_sessions_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event, speaker, _ = event_with_session(client, headers)
    assert client.get(url(event["id"])).json()[0]["speaker"]["name"] == "Ada"
    renamed = client.put(
        f"{SPEAKERS}/{speaker['id']}", json={"name": "Ada Lovelace", "bio": "bio"}, headers=headers
    )
    assert renamed.status_code == 200, renamed.text
    assert client.get(url(event["id"])).json()[0]["speaker"]["name"] == "Ada Lovelace"


def test_hidden_event_answers_404_to_anonymous_even_when_organizer_cached_sessions(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event, _, _ = event_with_session(client, headers, published=False)
    assert titles(client.get(url(event["id"]), headers=headers).json()) == ["Keynote"]
    assert client.get(url(event["id"])).status_code == 404


def test_hidden_event_stays_404_for_anonymous_after_publish_then_cancel(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event, _, _ = event_with_session(client, headers)
    assert client.get(url(event["id"])).status_code == 200
    cancelled = client.patch(
        f"/api/v1/events/{event['id']}/status", json={"status": "cancelled"}, headers=headers
    )
    assert cancelled.status_code == 200, cancelled.text
    assert client.get(url(event["id"])).status_code == 404
    assert client.get(url(event["id"]), headers=headers).status_code == 200


def test_missing_event_answers_404_and_nothing_is_cached(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    assert client.get(url(999)).status_code == 404
    assert fake_cache.sets == []


def test_each_event_has_its_own_entry(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    first, _, _ = event_with_session(client, headers)
    second = make_event(client, headers, name="Other")
    publish(client, headers, second["id"])
    assert len(client.get(url(first["id"])).json()) == 1
    assert client.get(url(second["id"])).json() == []
    assert len({key for _, key, _, _ in fake_cache.sets}) == 2


def test_entries_use_the_configured_sessions_ttl(
    client: TestClient,
    session: Session,
    fake_cache: FakeCache,
    override_settings: Callable[..., None],
) -> None:
    override_settings(cache_ttl_sessions_seconds=11)
    event, _, _ = event_with_session(client, organizer(client, session))
    client.get(url(event["id"]))
    assert [(ns, ttl) for ns, _, _, ttl in fake_cache.sets] == [(SESSIONS_NAMESPACE, 11)]


def test_sessions_answer_from_database_when_redis_is_down(
    client: TestClient, session: Session, unreachable_cache: object
) -> None:
    event, _, _ = event_with_session(client, organizer(client, session))
    response = client.get(url(event["id"]))
    assert response.status_code == 200
    assert titles(response.json()) == ["Keynote"]
    assert client.get(url(999)).status_code == 404
