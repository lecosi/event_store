from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.application.ports import EVENTS_NAMESPACE
from app.domain.enums import Role
from app.infrastructure.db.models import Event
from tests.fakes import FakeCache
from tests.test_events_api import EVENTS, create, make_user, organizer, publish


def names(response_json: dict) -> list[str]:
    return [item["name"] for item in response_json["items"]]


def rename_in_database(session: Session, event_id: int, name: str) -> None:
    row = session.exec(select(Event).where(Event.id == event_id)).one()
    row.name = name
    session.add(row)
    session.commit()


def published_event(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    event = create(client, headers, **overrides)
    publish(client, headers, event["id"])
    return event


def test_public_event_list_is_served_from_cache_on_second_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    event = published_event(client, organizer(client, session), name="Cached")
    first = client.get(EVENTS)
    rename_in_database(session, event["id"], "Renamed behind the cache")
    second = client.get(EVENTS)
    assert names(first.json()) == ["Cached"]
    assert second.json() == first.json()


def test_event_write_through_api_is_visible_on_next_public_list_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event = published_event(client, headers, name="Before")
    assert names(client.get(EVENTS).json()) == ["Before"]
    renamed = client.put(
        f"{EVENTS}/{event['id']}",
        json={
            **{k: event[k] for k in ("description", "location", "start_at", "end_at")},
            "name": "After",
            "capacity": event["capacity"],
        },
        headers=headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert names(client.get(EVENTS).json()) == ["After"]


def test_publishing_through_api_makes_event_appear_in_next_public_list_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    event = create(client, headers, name="Soon public")
    assert client.get(EVENTS).json()["total"] == 0
    publish(client, headers, event["id"])
    assert names(client.get(EVENTS).json()) == ["Soon public"]


def test_anonymous_never_receives_draft_after_organizer_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    published_event(client, headers, name="Public")
    create(client, headers, name="Secret draft")
    assert sorted(names(client.get(EVENTS, headers=headers).json())) == ["Public", "Secret draft"]
    assert names(client.get(EVENTS).json()) == ["Public"]


def test_organizer_sees_own_draft_after_anonymous_read(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    published_event(client, headers, name="Public")
    create(client, headers, name="Secret draft")
    assert names(client.get(EVENTS).json()) == ["Public"]
    assert sorted(names(client.get(EVENTS, headers=headers).json())) == ["Public", "Secret draft"]


def test_organizer_and_admin_views_neither_read_nor_write_the_cache(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    event = published_event(client, headers, name="Public")
    client.get(EVENTS)
    stored_entries = len(fake_cache.sets)
    rename_in_database(session, event["id"], "Fresh from database")
    assert names(client.get(EVENTS, headers=headers).json()) == ["Fresh from database"]
    assert names(client.get(EVENTS, headers=admin).json()) == ["Fresh from database"]
    assert len(fake_cache.sets) == stored_entries


def test_attendee_shares_the_public_entry_and_never_sees_drafts(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    published_event(client, headers, name="Public")
    create(client, headers, name="Secret draft")
    assert names(client.get(EVENTS, headers=attendee).json()) == ["Public"]
    assert names(client.get(EVENTS).json()) == ["Public"]
    assert len(fake_cache.sets) == 1


def test_former_organizer_now_attendee_never_leaks_own_draft_into_public_entry(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    published_event(client, headers, name="Public")
    create(client, headers, name="Secret draft")
    make_user(client, session, "org@example.com", Role.ATTENDEE)
    assert names(client.get(EVENTS, headers=headers).json()) == ["Public"]
    assert all("Secret draft" not in value for _, _, value, _ in fake_cache.sets)


def test_entries_differ_per_search_text_status_and_page(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    headers = organizer(client, session)
    published_event(client, headers, name="Alpha")
    published_event(client, headers, name="Beta")
    assert names(client.get(EVENTS, params={"q": "alpha"}).json()) == ["Alpha"]
    assert names(client.get(EVENTS, params={"q": "beta"}).json()) == ["Beta"]
    assert client.get(EVENTS, params={"status": "published"}).json()["total"] == 2
    assert client.get(EVENTS, params={"size": 1, "page": 2}).json()["page"] == 2
    assert len({key for _, key, _, _ in fake_cache.sets}) == 4


def test_cache_keys_never_contain_raw_search_text(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    client.get(EVENTS, params={"q": "secret-term:../*"})
    assert fake_cache.sets
    assert all("secret-term" not in key for _, key, _, _ in fake_cache.sets)


def test_entries_use_the_configured_events_ttl(
    client: TestClient,
    session: Session,
    fake_cache: FakeCache,
    override_settings: Callable[..., None],
) -> None:
    override_settings(cache_ttl_events_seconds=9)
    client.get(EVENTS)
    assert [(ns, ttl) for ns, _, _, ttl in fake_cache.sets] == [(EVENTS_NAMESPACE, 9)]


def test_event_detail_is_not_cached(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    event = published_event(client, organizer(client, session), name="Detail")
    fake_cache.sets.clear()
    assert client.get(f"{EVENTS}/{event['id']}").status_code == 200
    assert fake_cache.sets == []


def test_event_list_answers_from_database_when_redis_is_down(
    client: TestClient, session: Session, unreachable_cache: object
) -> None:
    published_event(client, organizer(client, session), name="Public")
    response = client.get(EVENTS)
    assert response.status_code == 200
    assert names(response.json()) == ["Public"]
