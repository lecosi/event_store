from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domain.enums import Role
from tests.test_events_api import EVENTS, create, make_user, organizer

SPEAKERS = "/api/v1/speakers"


def base() -> datetime:
    return datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=10)


def iso(hours: int) -> str:
    return (base() + timedelta(hours=hours)).isoformat()


def make_event(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    fields: dict[str, object] = {"start_at": iso(0), "end_at": iso(8), "capacity": 30}
    fields.update(overrides)
    return create(client, headers, **fields)


def make_speaker(client: TestClient, headers: dict[str, str], name: str = "Ada") -> dict:
    response = client.post(SPEAKERS, json={"name": name, "bio": "bio"}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def session_body(speaker_id: int, start: int = 1, end: int = 2, **overrides: object) -> dict:
    body: dict[str, object] = {
        "title": "Keynote",
        "speaker_id": speaker_id,
        "start_at": iso(start),
        "end_at": iso(end),
        "capacity": 10,
    }
    body.update(overrides)
    return body


def event_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "PyCon",
        "description": "",
        "location": "Lima",
        "start_at": iso(0),
        "end_at": iso(8),
        "capacity": 30,
    }
    body.update(overrides)
    return body


def url(event_id: int, session_id: int | None = None) -> str:
    suffix = f"/{session_id}" if session_id else ""
    return f"{EVENTS}/{event_id}/sessions{suffix}"


def test_create_requires_auth_and_organizer_role(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    speaker = make_speaker(client, headers)
    body = session_body(speaker["id"])
    assert client.post(url(event["id"]), json=body).status_code == 401
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    assert client.post(url(event["id"]), json=body, headers=attendee).status_code == 403


def test_only_owner_or_admin_can_manage(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    speaker = make_speaker(client, headers)
    body = session_body(speaker["id"])
    stranger = make_user(client, session, "other@example.com", Role.ORGANIZER)
    assert client.post(url(event["id"]), json=body, headers=stranger).status_code == 403
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    created = client.post(url(event["id"]), json=body, headers=admin)
    assert created.status_code == 201
    sid = created.json()["id"]
    assert client.put(url(event["id"], sid), json=body, headers=stranger).status_code == 403
    assert client.delete(url(event["id"], sid), headers=stranger).status_code == 403


def test_create_update_delete_and_list(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    speaker = make_speaker(client, headers)
    created = client.post(url(event["id"]), json=session_body(speaker["id"]), headers=headers)
    assert created.status_code == 201, created.text
    sid = created.json()["id"]
    assert created.json()["speaker"] == {"id": speaker["id"], "name": "Ada"}

    updated = client.put(
        url(event["id"], sid),
        json=session_body(speaker["id"], title="Renamed"),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed"

    assert [s["id"] for s in client.get(url(event["id"]), headers=headers).json()] == [sid]
    assert client.delete(url(event["id"], sid), headers=headers).status_code == 204
    assert client.get(url(event["id"]), headers=headers).json() == []
    assert client.delete(url(event["id"], sid), headers=headers).status_code == 404


def test_schedule_and_capacity_validation(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    sp = make_speaker(client, headers)["id"]
    eid = event["id"]

    def post(body: dict) -> int:
        return client.post(url(eid), json=body, headers=headers).status_code

    assert post(session_body(sp, 3, 3)) == 422
    assert post(session_body(sp, -1, 1)) == 422
    assert post(session_body(sp, 7, 9)) == 422
    assert post(session_body(sp, capacity=31)) == 422
    assert post(session_body(sp, capacity=0)) == 422
    assert post(session_body(999)) == 422


def test_speaker_overlap_conflict_adjacent_allowed_and_self_excluded(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    other_event = make_event(client, headers)
    sp = make_speaker(client, headers)["id"]
    first = client.post(url(event["id"]), json=session_body(sp, 1, 3), headers=headers).json()

    overlapping = session_body(sp, 2, 4)
    assert client.post(url(event["id"]), json=overlapping, headers=headers).status_code == 409
    assert client.post(url(other_event["id"]), json=overlapping, headers=headers).status_code == 409
    adjacent = session_body(sp, 3, 4)
    assert client.post(url(event["id"]), json=adjacent, headers=headers).status_code == 201

    same_slot = session_body(sp, 1, 3, title="Edited")
    assert (
        client.put(url(event["id"], first["id"]), json=same_slot, headers=headers).status_code
        == 200
    )


def test_closed_event_rejects_session_changes(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    sp = make_speaker(client, headers)["id"]
    sid = client.post(url(event["id"]), json=session_body(sp), headers=headers).json()["id"]
    cancel = client.patch(
        f"{EVENTS}/{event['id']}/status", json={"status": "cancelled"}, headers=headers
    )
    assert cancel.status_code == 200
    body = session_body(sp, 3, 4)
    assert client.post(url(event["id"]), json=body, headers=headers).status_code == 409
    assert client.put(url(event["id"], sid), json=body, headers=headers).status_code == 409
    assert client.delete(url(event["id"], sid), headers=headers).status_code == 409


def test_unknown_event_is_404(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    sp = make_speaker(client, headers)["id"]
    assert client.post(url(999), json=session_body(sp), headers=headers).status_code == 404
    assert client.get(url(999)).status_code == 404


def test_event_detail_includes_sessions_ordered_with_speaker(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    ada = make_speaker(client, headers, "Ada")["id"]
    bob = make_speaker(client, headers, "Bob")["id"]
    client.post(url(event["id"]), json=session_body(ada, 5, 6, title="Late"), headers=headers)
    client.post(url(event["id"]), json=session_body(bob, 1, 2, title="Early"), headers=headers)
    client.patch(f"{EVENTS}/{event['id']}/status", json={"status": "published"}, headers=headers)

    detail = client.get(f"{EVENTS}/{event['id']}").json()
    assert [s["title"] for s in detail["sessions"]] == ["Early", "Late"]
    assert detail["sessions"][0]["speaker"] == {"id": bob, "name": "Bob"}


def test_lowering_event_capacity_below_largest_session_conflicts(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    sp = make_speaker(client, headers)["id"]
    client.post(url(event["id"]), json=session_body(sp, capacity=20), headers=headers)
    event_url = f"{EVENTS}/{event['id']}"
    lowered = event_body(capacity=19)
    assert client.put(event_url, json=lowered, headers=headers).status_code == 409
    exact = event_body(capacity=20)
    assert client.put(event_url, json=exact, headers=headers).status_code == 200


def test_changing_event_dates_must_keep_sessions_inside(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    sp = make_speaker(client, headers)["id"]
    client.post(url(event["id"]), json=session_body(sp, start=2, end=4), headers=headers)
    event_url = f"{EVENTS}/{event['id']}"
    starts_after_session = client.put(
        event_url, json=event_body(start_at=iso(3), end_at=iso(8)), headers=headers
    )
    assert starts_after_session.status_code == 409
    assert "sessions" in starts_after_session.json()["detail"]
    ends_before_session = client.put(
        event_url, json=event_body(start_at=iso(1), end_at=iso(3)), headers=headers
    )
    assert ends_before_session.status_code == 409
    exact_bounds = client.put(
        event_url, json=event_body(start_at=iso(2), end_at=iso(4)), headers=headers
    )
    assert exact_bounds.status_code == 200
