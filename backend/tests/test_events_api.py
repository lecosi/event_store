from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domain.enums import Role
from app.infrastructure.db.models import Event, Speaker, User
from app.infrastructure.db.models import Session as SessionRow

EVENTS = "/api/v1/events"


def future(days: int) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "PyCon",
        "description": "Python conference",
        "location": "Lima",
        "start_at": future(10),
        "end_at": future(11),
        "capacity": 50,
    }
    body.update(overrides)
    return body


def make_user(client: TestClient, session: Session, email: str, role: Role) -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})
    user = session.exec(select(User).where(User.email == email)).one()
    user.role = role
    session.add(user)
    session.commit()
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def organizer(client: TestClient, session: Session) -> dict[str, str]:
    return make_user(client, session, "org@example.com", Role.ORGANIZER)


def create(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post(EVENTS, json=payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def publish(client: TestClient, headers: dict[str, str], event_id: int) -> None:
    response = client.patch(
        f"{EVENTS}/{event_id}/status", json={"status": "published"}, headers=headers
    )
    assert response.status_code == 200, response.text


def test_create_requires_auth_and_role(client: TestClient, session: Session) -> None:
    assert client.post(EVENTS, json=payload()).status_code == 401
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    assert client.post(EVENTS, json=payload(), headers=attendee).status_code == 403


def test_attendee_account_gets_403_creating_event(client: TestClient, session: Session) -> None:
    headers = make_user(client, session, "att@example.com", Role.ATTENDEE)
    assert client.post(EVENTS, json=payload(), headers=headers).status_code == 403


def test_create_ok_defaults_to_draft(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    body = create(client, headers)
    assert body["status"] == "draft"
    assert body["name"] == "PyCon"
    assert body["sessions"] == []


def test_create_validation(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    bad = [
        payload(capacity=0),
        payload(start_at=future(5), end_at=future(4)),
        payload(start_at=future(-1), end_at=future(2)),
        payload(name=""),
    ]
    for body in bad:
        assert client.post(EVENTS, json=body, headers=headers).status_code == 422


def test_get_event_public_when_published_and_hidden_when_draft(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = create(client, headers)
    url = f"{EVENTS}/{event['id']}"
    assert client.get(url).status_code == 404
    assert client.get(url, headers=headers).status_code == 200
    publish(client, headers, event["id"])
    assert client.get(url).status_code == 200
    assert client.get(f"{EVENTS}/9999").status_code == 404


def test_update_permissions_and_ownership(client: TestClient, session: Session) -> None:
    owner = organizer(client, session)
    other = make_user(client, session, "other@example.com", Role.ORGANIZER)
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    event = create(client, owner)
    url = f"{EVENTS}/{event['id']}"
    body = payload(name="Renamed")

    assert client.put(url, json=body).status_code == 401
    assert client.put(url, json=body, headers=attendee).status_code == 403
    assert client.put(url, json=body, headers=other).status_code == 403
    assert client.put(url, json=body, headers=owner).json()["name"] == "Renamed"
    assert client.put(url, json=payload(name="ByAdmin"), headers=admin).json()["name"] == "ByAdmin"
    assert client.put(f"{EVENTS}/9999", json=body, headers=owner).status_code == 404


def test_cannot_edit_cancelled_event(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    event = create(client, headers)
    url = f"{EVENTS}/{event['id']}"
    cancel = client.patch(f"{url}/status", json={"status": "cancelled"}, headers=headers)
    assert cancel.status_code == 200
    assert client.put(url, json=payload(), headers=headers).status_code == 409


def test_status_transitions(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    other = make_user(client, session, "other@example.com", Role.ORGANIZER)
    event = create(client, headers)
    url = f"{EVENTS}/{event['id']}/status"

    assert client.patch(url, json={"status": "published"}).status_code == 401
    assert client.patch(url, json={"status": "published"}, headers=other).status_code == 403
    assert client.patch(url, json={"status": "finished"}, headers=headers).status_code == 409
    assert client.patch(url, json={"status": "bogus"}, headers=headers).status_code == 422
    assert client.patch(url, json={"status": "published"}, headers=headers).json()["status"] == (
        "published"
    )
    assert client.patch(url, json={"status": "draft"}, headers=headers).status_code == 409
    assert client.patch(url, json={"status": "finished"}, headers=headers).status_code == 200
    assert client.patch(url, json={"status": "cancelled"}, headers=headers).status_code == 409


def test_delete_permissions(client: TestClient, session: Session) -> None:
    owner = organizer(client, session)
    other = make_user(client, session, "other@example.com", Role.ORGANIZER)
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    first = create(client, owner)
    second = create(client, owner)

    assert client.delete(f"{EVENTS}/{first['id']}").status_code == 401
    assert client.delete(f"{EVENTS}/{first['id']}", headers=other).status_code == 403
    assert client.delete(f"{EVENTS}/{first['id']}", headers=owner).status_code == 204
    assert client.delete(f"{EVENTS}/{first['id']}", headers=owner).status_code == 404
    assert client.delete(f"{EVENTS}/{second['id']}", headers=admin).status_code == 204
    assert session.exec(select(Event)).all() == []


def test_delete_removes_sessions(client: TestClient, session: Session) -> None:
    owner = organizer(client, session)
    event = create(client, owner)
    speaker = Speaker(name="Ada")
    session.add(speaker)
    session.commit()
    session.add(
        SessionRow(
            event_id=event["id"],
            speaker_id=speaker.id,
            title="Keynote",
            start_at=datetime.fromisoformat(event["start_at"]),
            end_at=datetime.fromisoformat(event["end_at"]),
            capacity=5,
        )
    )
    session.commit()
    assert client.delete(f"{EVENTS}/{event['id']}", headers=owner).status_code == 204
    assert session.exec(select(SessionRow)).all() == []
    assert session.exec(select(Speaker)).all() == [speaker]


def seed_published(client: TestClient, headers: dict[str, str], names: list[str]) -> None:
    for index, name in enumerate(names):
        event = create(
            client, headers, name=name, start_at=future(10 + index), end_at=future(20 + index)
        )
        publish(client, headers, event["id"])


def test_list_public_shows_only_published(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    seed_published(client, headers, ["Visible"])
    create(client, headers, name="Hidden draft")

    public = client.get(EVENTS).json()
    assert [e["name"] for e in public["items"]] == ["Visible"]
    mine = client.get(EVENTS, headers=headers).json()
    assert sorted(e["name"] for e in mine["items"]) == ["Hidden draft", "Visible"]
    other = make_user(client, session, "other@example.com", Role.ORGANIZER)
    assert client.get(EVENTS, headers=other).json()["total"] == 1
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    assert client.get(EVENTS, headers=admin).json()["total"] == 2
    drafts = client.get(EVENTS, params={"status": "draft"}, headers=admin).json()
    assert [e["name"] for e in drafts["items"]] == ["Hidden draft"]
    assert client.get(EVENTS, params={"status": "draft"}).json()["total"] == 0


def test_list_invalid_bearer_is_treated_as_anonymous(client: TestClient) -> None:
    response = client.get(EVENTS, headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 200


def test_list_pagination_math_and_order(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    seed_published(client, headers, [f"Event {i:02d}" for i in range(25)])

    first = client.get(EVENTS, params={"page": 1, "size": 10}).json()
    assert (first["total"], first["page"], first["size"], first["pages"]) == (25, 1, 10, 3)
    assert [e["name"] for e in first["items"]][:2] == ["Event 00", "Event 01"]
    last = client.get(EVENTS, params={"page": 3, "size": 10}).json()
    assert len(last["items"]) == 5
    beyond = client.get(EVENTS, params={"page": 4, "size": 10}).json()
    assert beyond["items"] == [] and beyond["total"] == 25
    default = client.get(EVENTS).json()
    assert (default["page"], default["size"], len(default["items"])) == (1, 10, 10)


def test_list_param_validation(client: TestClient) -> None:
    for params in ({"page": 0}, {"size": 0}, {"size": 101}, {"status": "bogus"}):
        assert client.get(EVENTS, params=params).status_code == 422


def test_search_partial_and_case_insensitive(client: TestClient, session: Session) -> None:
    headers = organizer(client, session)
    seed_published(client, headers, ["Python Conference", "Rust Meetup", "PYTHON Workshop"])

    def search(term: str) -> list[str]:
        items = client.get(EVENTS, params={"q": term}).json()["items"]
        return sorted(e["name"] for e in items)

    assert search("python") == ["PYTHON Workshop", "Python Conference"]
    assert search("meet") == ["Rust Meetup"]
    assert search("nothing") == []
    assert len(search("")) == 3


def test_search_escapes_wildcards_and_resists_injection(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    seed_published(client, headers, ["100% Fun", "Plain event", "a_b", "axb", "back\\slash"])

    def search(term: str) -> list[str]:
        items = client.get(EVENTS, params={"q": term}).json()["items"]
        return sorted(e["name"] for e in items)

    assert search("' OR 1=1 --") == []
    assert search("'; DROP TABLE event; --") == []
    assert search("%") == ["100% Fun"]
    assert search("_") == ["a_b"]
    assert search("a_b") == ["a_b"]
    assert search("\\") == ["back\\slash"]
    assert client.get(EVENTS).json()["total"] == 5
