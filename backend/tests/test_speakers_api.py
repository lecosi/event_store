from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domain.enums import Role
from tests.test_events_api import make_user, organizer
from tests.test_sessions_api import SPEAKERS, make_event, make_speaker, session_body, url


def body(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {"name": "Ada", "bio": "Pioneer", "email": "ada@example.com"}
    fields.update(overrides)
    return fields


def test_writes_require_auth_and_organizer(client: TestClient, session: Session) -> None:
    assert client.post(SPEAKERS, json=body()).status_code == 401
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    assert client.post(SPEAKERS, json=body(), headers=attendee).status_code == 403
    assert client.put(f"{SPEAKERS}/1", json=body(), headers=attendee).status_code == 403
    assert client.delete(f"{SPEAKERS}/1", headers=attendee).status_code == 403


def test_crud_and_public_reads(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    created = client.post(SPEAKERS, json=body(), headers=headers)
    assert created.status_code == 201
    sid = created.json()["id"]

    assert client.get(f"{SPEAKERS}/{sid}").json()["name"] == "Ada"
    assert [s["id"] for s in client.get(SPEAKERS).json()["items"]] == [sid]

    updated = client.put(f"{SPEAKERS}/{sid}", json=body(name="Ada L."), headers=headers)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Ada L."

    assert client.delete(f"{SPEAKERS}/{sid}", headers=headers).status_code == 204
    assert client.get(f"{SPEAKERS}/{sid}").status_code == 404
    assert client.delete(f"{SPEAKERS}/{sid}", headers=headers).status_code == 404


def test_email_is_optional_and_unique_when_provided(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    assert client.post(SPEAKERS, json=body(), headers=headers).status_code == 201
    assert client.post(SPEAKERS, json=body(), headers=headers).status_code == 409
    for _ in range(2):
        response = client.post(SPEAKERS, json={"name": "NoMail"}, headers=headers)
        assert response.status_code == 201
        assert response.json()["email"] is None


def test_duplicate_email_is_case_insensitive_409(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    assert client.post(SPEAKERS, json=body(), headers=headers).status_code == 201
    upper = body(email="ADA@Example.com")
    assert client.post(SPEAKERS, json=upper, headers=headers).status_code == 409


def test_invalid_payload_is_422(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    assert client.post(SPEAKERS, json=body(name=""), headers=headers).status_code == 422
    assert client.post(SPEAKERS, json=body(email="nope"), headers=headers).status_code == 422


def test_delete_with_sessions_is_409(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    speaker = make_speaker(client, headers)
    client.post(url(event["id"]), json=session_body(speaker["id"]), headers=headers)
    assert client.delete(f"{SPEAKERS}/{speaker['id']}", headers=headers).status_code == 409


def seed_speakers(client: TestClient, headers: dict[str, str], names: list[str]) -> None:
    for index, name in enumerate(names):
        response = client.post(
            SPEAKERS, json=body(name=name, email=f"s{index}@example.com"), headers=headers
        )
        assert response.status_code == 201


def test_list_is_paginated_public_and_ordered_by_name(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    seed_speakers(client, headers, [f"Speaker {n:02d}" for n in range(12, 0, -1)])

    first = client.get(SPEAKERS)
    assert first.status_code == 200
    data = first.json()
    assert (data["total"], data["page"], data["size"], data["pages"]) == (12, 1, 10, 2)
    assert [s["name"] for s in data["items"]] == [f"Speaker {n:02d}" for n in range(1, 11)]

    second = client.get(SPEAKERS, params={"page": 2}).json()
    assert [s["name"] for s in second["items"]] == ["Speaker 11", "Speaker 12"]
    assert client.get(SPEAKERS, params={"page": 3}).json()["items"] == []
    assert client.get(SPEAKERS, params={"size": 5}).json()["pages"] == 3


def test_empty_list_has_zero_pages(client: TestClient) -> None:
    data = client.get(SPEAKERS).json()
    assert data == {"items": [], "total": 0, "page": 1, "size": 10, "pages": 0}


def test_search_is_case_insensitive_and_counts_matches(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    seed_speakers(client, headers, ["Grace Hopper", "Ada Lovelace", "Margaret Hamilton"])

    data = client.get(SPEAKERS, params={"q": "GRACE"}).json()
    assert [s["name"] for s in data["items"]] == ["Grace Hopper"]
    assert data["total"] == 1
    assert client.get(SPEAKERS, params={"q": "a"}).json()["total"] == 3
    assert client.get(SPEAKERS, params={"q": "zzz"}).json()["total"] == 0
    assert client.get(SPEAKERS, params={"q": "  "}).json()["total"] == 3


def test_search_escapes_wildcards_and_resists_injection(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    seed_speakers(client, headers, ["100% Real", "Plain", "a_b", "axb", "back\\slash"])

    def search(term: str) -> list[str]:
        items = client.get(SPEAKERS, params={"q": term}).json()["items"]
        return sorted(s["name"] for s in items)

    assert search("%") == ["100% Real"]
    assert search("_") == ["a_b"]
    assert search("a_b") == ["a_b"]
    assert search("\\") == ["back\\slash"]
    assert search("' OR 1=1 --") == []
    assert client.get(SPEAKERS).json()["total"] == 5


def test_invalid_pagination_is_rejected(client: TestClient) -> None:
    for params in ({"page": 0}, {"size": 0}, {"size": 101}):
        assert client.get(SPEAKERS, params=params).status_code == 422
