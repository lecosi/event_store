from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session

from app.domain.enums import Role
from tests.test_events_api import EVENTS, create, future, make_user, organizer, publish

ME = "/api/v1/users/me/events"


def published_event(client: TestClient, session: Session, **overrides: object) -> int:
    headers = organizer(client, session)
    event = create(client, headers, **overrides)
    publish(client, headers, event["id"])
    return event["id"]


def attendee(client: TestClient, session: Session, n: int) -> dict[str, str]:
    return make_user(client, session, f"att{n}@example.com", Role.ATTENDEE)


def register(client: TestClient, headers: dict[str, str], event_id: int) -> Response:
    return client.post(f"{EVENTS}/{event_id}/register", headers=headers)


def test_register_requires_auth(client: TestClient, session: Session) -> None:
    event_id = published_event(client, session)
    assert client.post(f"{EVENTS}/{event_id}/register").status_code == 401
    assert client.delete(f"{EVENTS}/{event_id}/register").status_code == 401
    assert client.get(ME).status_code == 401


def test_register_success_and_detail_availability(client: TestClient, session: Session) -> None:
    event_id = published_event(client, session, capacity=3)
    headers = attendee(client, session, 1)
    response = register(client, headers, event_id)
    assert response.status_code == 201
    assert response.json()["event_id"] == event_id

    mine = client.get(f"{EVENTS}/{event_id}", headers=headers).json()
    assert (mine["registered_count"], mine["available_spots"], mine["is_registered"]) == (
        1,
        2,
        True,
    )
    anonymous = client.get(f"{EVENTS}/{event_id}").json()
    assert (anonymous["registered_count"], anonymous["is_registered"]) == (1, False)


def test_duplicate_registration_is_conflict(client: TestClient, session: Session) -> None:
    event_id = published_event(client, session)
    headers = attendee(client, session, 1)
    assert register(client, headers, event_id).status_code == 201
    assert register(client, headers, event_id).status_code == 409


def test_filling_event_rejects_next_user(client: TestClient, session: Session) -> None:
    event_id = published_event(client, session, capacity=2)
    for n in (1, 2):
        assert register(client, attendee(client, session, n), event_id).status_code == 201
    response = register(client, attendee(client, session, 3), event_id)
    assert response.status_code == 409
    assert "full" in response.json()["detail"]
    detail = client.get(f"{EVENTS}/{event_id}").json()
    assert (detail["registered_count"], detail["available_spots"]) == (2, 0)


def test_cannot_register_to_draft_or_cancelled(client: TestClient, session: Session) -> None:
    org = organizer(client, session)
    draft = create(client, org)["id"]
    headers = attendee(client, session, 1)
    assert register(client, headers, draft).status_code == 404
    assert register(client, org, draft).status_code == 409

    published = create(client, org)["id"]
    publish(client, org, published)
    client.patch(f"{EVENTS}/{published}/status", json={"status": "cancelled"}, headers=org)
    assert register(client, headers, published).status_code == 404
    assert register(client, org, published).status_code == 409


def test_register_unknown_event(client: TestClient, session: Session) -> None:
    assert register(client, attendee(client, session, 1), 999).status_code == 404


def test_unregister(client: TestClient, session: Session) -> None:
    event_id = published_event(client, session, capacity=1)
    headers = attendee(client, session, 1)
    assert client.delete(f"{EVENTS}/{event_id}/register", headers=headers).status_code == 404
    register(client, headers, event_id)
    assert client.delete(f"{EVENTS}/{event_id}/register", headers=headers).status_code == 204
    assert register(client, attendee(client, session, 2), event_id).status_code == 201


def test_unregister_rejected_when_finished(client: TestClient, session: Session) -> None:
    org = organizer(client, session)
    event_id = create(client, org)["id"]
    publish(client, org, event_id)
    headers = attendee(client, session, 1)
    register(client, headers, event_id)
    client.patch(f"{EVENTS}/{event_id}/status", json={"status": "finished"}, headers=org)
    assert client.delete(f"{EVENTS}/{event_id}/register", headers=headers).status_code == 409


def test_my_events_pagination_and_order(client: TestClient, session: Session) -> None:
    org = organizer(client, session)
    ids = {}
    for days in (9, 3, 6):
        event = create(
            client,
            org,
            name=f"E{days}",
            start_at=future(days),
            end_at=future(days + 1),
        )
        publish(client, org, event["id"])
        ids[days] = event["id"]
    headers = attendee(client, session, 1)
    for event_id in ids.values():
        register(client, headers, event_id)
    register(client, attendee(client, session, 2), ids[3])

    page1 = client.get(ME, params={"page": 1, "size": 2}, headers=headers).json()
    assert [e["name"] for e in page1["items"]] == ["E3", "E6"]
    assert (page1["total"], page1["pages"], page1["page"], page1["size"]) == (3, 2, 1, 2)
    assert "registered_at" in page1["items"][0]
    page2 = client.get(ME, params={"page": 2, "size": 2}, headers=headers).json()
    assert [e["name"] for e in page2["items"]] == ["E9"]
