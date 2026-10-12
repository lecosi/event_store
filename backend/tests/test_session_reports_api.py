import csv
import io
import re
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domain.enums import Role
from app.infrastructure.db.models import User
from tests.test_events_api import EVENTS, create, make_user, publish
from tests.test_sessions_api import make_speaker

JSON_URL = "/api/v1/reports/sessions/participants"
CSV_URL = "/api/v1/reports/sessions/participants.csv"
BOM = "﻿"
HEADER = "Nombre completo;Correo electrónico;Evento;Sesión;Inicio de la sesión"

Headers = dict[str, str]


@dataclass
class World:
    client: TestClient
    session: Session
    org_a: Headers
    org_b: Headers
    admin: Headers
    attendee: Headers
    counter: int = 0

    def event(self, owner: Headers, name: str = "PyCon", publish_it: bool = True) -> int:
        created = create(
            self.client,
            owner,
            name=name,
            start_at="2030-03-01T00:00:00Z",
            end_at="2030-03-31T00:00:00Z",
            capacity=100,
        )
        if publish_it:
            publish(self.client, owner, created["id"])
        return created["id"]

    def talk(
        self,
        owner: Headers,
        event_id: int,
        title: str = "Keynote",
        start_at: str = "2030-03-10T09:00:00Z",
        end_at: str | None = None,
    ) -> int:
        self.counter += 1
        speaker = make_speaker(self.client, owner, name=f"Speaker {self.counter}")
        response = self.client.post(
            f"{EVENTS}/{event_id}/sessions",
            json={
                "title": title,
                "speaker_id": speaker["id"],
                "start_at": start_at,
                "end_at": end_at or start_at.replace("T09", "T10"),
                "capacity": 50,
            },
            headers=owner,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def enroll(
        self, event_id: int, session_id: int, full_name: str, email: str | None = None
    ) -> Headers:
        self.counter += 1
        address = email or f"person{self.counter}@example.com"
        headers = make_user(self.client, self.session, address, Role.ATTENDEE)
        user = self.session.exec(select(User).where(User.email == address)).one()
        user.full_name = full_name
        self.session.add(user)
        self.session.commit()
        registered = self.client.post(f"{EVENTS}/{event_id}/register", headers=headers)
        assert registered.status_code == 201, registered.text
        enrolled = self.client.post(
            f"{EVENTS}/{event_id}/sessions/{session_id}/register", headers=headers
        )
        assert enrolled.status_code == 201, enrolled.text
        return headers


@pytest.fixture
def world(client: TestClient, session: Session) -> World:
    org_a = make_user(client, session, "orga@example.com", Role.ORGANIZER)
    return World(
        client=client,
        session=session,
        org_a=org_a,
        org_b=make_user(client, session, "orgb@example.com", Role.ORGANIZER),
        admin=make_user(client, session, "admin@example.com", Role.ADMIN),
        attendee=make_user(client, session, "attendee@example.com", Role.ATTENDEE),
    )


def names(response_json: dict) -> list[str]:
    return [item["full_name"] for item in response_json["items"]]


def csv_rows(body: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(body.removeprefix(BOM), newline=""), delimiter=";"))


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_report_requires_authentication(client: TestClient, url: str) -> None:
    assert client.get(url).status_code == 401


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_attendee_cannot_read_the_report(world: World, url: str) -> None:
    response = world.client.get(url, headers=world.attendee)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_row_exposes_person_event_session_and_start(world: World) -> None:
    event_id = world.event(world.org_a, "PyCon")
    session_id = world.talk(world.org_a, event_id, "Keynote", "2030-03-10T09:00:00Z")
    world.enroll(event_id, session_id, "Ana Gomez", "ana@example.com")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert body["items"] == [
        {
            "full_name": "Ana Gomez",
            "email": "ana@example.com",
            "event_name": "PyCon",
            "session_title": "Keynote",
            "session_start": "2030-03-10T09:00:00Z",
        }
    ]
    assert body["total"] == 1


def test_event_registration_without_session_enrollment_does_not_appear(world: World) -> None:
    event_id = world.event(world.org_a)
    world.talk(world.org_a, event_id)
    headers = make_user(world.client, world.session, "reg@example.com", Role.ATTENDEE)
    world.client.post(f"{EVENTS}/{event_id}/register", headers=headers)

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert body["items"] == []


def test_organizer_sees_only_enrollments_of_own_events(world: World) -> None:
    mine = world.event(world.org_a, "Mine")
    theirs = world.event(world.org_b, "Theirs")
    world.enroll(mine, world.talk(world.org_a, mine), "Ana Gomez")
    world.enroll(theirs, world.talk(world.org_b, theirs), "Luis Perez")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert names(body) == ["Ana Gomez"]


def test_admin_sees_enrollments_of_every_event(world: World) -> None:
    mine = world.event(world.org_a, "Mine")
    theirs = world.event(world.org_b, "Theirs")
    world.enroll(mine, world.talk(world.org_a, mine, start_at="2030-03-10T09:00:00Z"), "Ana Gomez")
    world.enroll(
        theirs, world.talk(world.org_b, theirs, start_at="2030-03-11T09:00:00Z"), "Luis Perez"
    )

    body = world.client.get(JSON_URL, headers=world.admin).json()

    assert names(body) == ["Ana Gomez", "Luis Perez"]


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_foreign_event_id_is_forbidden_for_organizer(world: World, url: str) -> None:
    theirs = world.event(world.org_b)

    response = world.client.get(url, params={"event_id": theirs}, headers=world.org_a)

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_foreign_session_id_is_forbidden_for_organizer(world: World, url: str) -> None:
    theirs = world.event(world.org_b)
    foreign_session = world.talk(world.org_b, theirs)

    response = world.client.get(url, params={"session_id": foreign_session}, headers=world.org_a)

    assert response.status_code == 403


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_unknown_event_id_is_not_found(world: World, url: str) -> None:
    response = world.client.get(url, params={"event_id": 999}, headers=world.org_a)

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_unknown_session_id_is_not_found(world: World, url: str) -> None:
    response = world.client.get(url, params={"session_id": 999}, headers=world.org_a)

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found"}


def test_session_id_filter_limits_the_report_to_one_session(world: World) -> None:
    event_id = world.event(world.org_a)
    keynote = world.talk(world.org_a, event_id, "Keynote", "2030-03-10T09:00:00Z")
    workshop = world.talk(world.org_a, event_id, "Workshop", "2030-03-11T09:00:00Z")
    world.enroll(event_id, keynote, "Ana Gomez")
    world.enroll(event_id, workshop, "Luis Perez")

    body = world.client.get(JSON_URL, params={"session_id": workshop}, headers=world.org_a).json()

    assert names(body) == ["Luis Perez"]


def test_event_id_filter_limits_the_report_to_one_event(world: World) -> None:
    first = world.event(world.org_a, "First")
    second = world.event(world.org_a, "Second")
    world.enroll(first, world.talk(world.org_a, first), "Ana Gomez")
    world.enroll(second, world.talk(world.org_a, second), "Luis Perez")

    body = world.client.get(JSON_URL, params={"event_id": second}, headers=world.org_a).json()

    assert names(body) == ["Luis Perez"]


def test_session_without_enrollments_gives_an_empty_page(world: World) -> None:
    session_id = world.talk(world.org_a, world.event(world.org_a))

    body = world.client.get(JSON_URL, params={"session_id": session_id}, headers=world.org_a).json()

    assert body == {"items": [], "total": 0, "page": 1, "size": 10, "pages": 0}


def test_q_matches_session_title_or_event_name_ignoring_case(world: World) -> None:
    pycon = world.event(world.org_a, "PyCon Latam")
    other = world.event(world.org_a, "JSConf")
    world.enroll(pycon, world.talk(world.org_a, pycon, "Keynote", "2030-03-10T09:00:00Z"), "Ana")
    world.enroll(
        other, world.talk(world.org_a, other, "Python intro", "2030-03-11T09:00:00Z"), "Luis"
    )
    world.enroll(other, world.talk(world.org_a, other, "Rust", "2030-03-12T09:00:00Z"), "Eva")

    body = world.client.get(JSON_URL, params={"q": "PYTHON"}, headers=world.org_a).json()
    by_event = world.client.get(JSON_URL, params={"q": "pycon"}, headers=world.org_a).json()

    assert names(body) == ["Luis"]
    assert names(by_event) == ["Ana"]


def test_q_does_not_search_participant_names(world: World) -> None:
    event_id = world.event(world.org_a)
    world.enroll(event_id, world.talk(world.org_a, event_id), "Ana Gomez")

    body = world.client.get(JSON_URL, params={"q": "Gomez"}, headers=world.org_a).json()

    assert body["items"] == []


def test_q_treats_like_wildcards_literally(world: World) -> None:
    event_id = world.event(world.org_a)
    percent = world.talk(world.org_a, event_id, "100% Python", "2030-03-10T09:00:00Z")
    plain = world.talk(world.org_a, event_id, "100 Python", "2030-03-11T09:00:00Z")
    world.enroll(event_id, percent, "Ana Gomez")
    world.enroll(event_id, plain, "Luis Perez")

    body = world.client.get(JSON_URL, params={"q": "%"}, headers=world.org_a).json()

    assert names(body) == ["Ana Gomez"]


def test_q_longer_than_200_characters_is_rejected(world: World) -> None:
    response = world.client.get(JSON_URL, params={"q": "x" * 201}, headers=world.org_a)

    assert response.status_code == 422


def test_status_filter_uses_the_event_status(world: World) -> None:
    live = world.event(world.org_a, "Live")
    world.enroll(live, world.talk(world.org_a, live), "Ana Gomez")

    published = world.client.get(
        JSON_URL, params={"status": "published"}, headers=world.org_a
    ).json()
    drafts = world.client.get(JSON_URL, params={"status": "draft"}, headers=world.org_a).json()

    assert names(published) == ["Ana Gomez"]
    assert drafts["items"] == []


def test_invalid_status_is_rejected(world: World) -> None:
    response = world.client.get(JSON_URL, params={"status": "nope"}, headers=world.org_a)

    assert response.status_code == 422


def test_date_range_is_inclusive_on_the_session_start_in_utc(world: World) -> None:
    event_id = world.event(world.org_a)
    midnight = world.talk(
        world.org_a, event_id, "Midnight", "2030-03-10T00:00:00Z", "2030-03-10T01:00:00Z"
    )
    late = world.talk(world.org_a, event_id, "Late", "2030-03-10T23:00:00Z", "2030-03-10T23:59:59Z")
    next_day = world.talk(
        world.org_a, event_id, "Next", "2030-03-11T00:00:00Z", "2030-03-11T01:00:00Z"
    )
    world.enroll(event_id, midnight, "Ana Gomez")
    world.enroll(event_id, late, "Luis Perez")
    world.enroll(event_id, next_day, "Eva Ruiz")

    day = world.client.get(
        JSON_URL,
        params={"date_from": "2030-03-10", "date_to": "2030-03-10"},
        headers=world.org_a,
    ).json()
    from_next = world.client.get(
        JSON_URL, params={"date_from": "2030-03-11"}, headers=world.org_a
    ).json()

    assert names(day) == ["Ana Gomez", "Luis Perez"]
    assert names(from_next) == ["Eva Ruiz"]


@pytest.mark.parametrize("url", [JSON_URL, CSV_URL])
def test_date_to_before_date_from_is_rejected(world: World, url: str) -> None:
    response = world.client.get(
        url, params={"date_from": "2030-03-10", "date_to": "2030-03-09"}, headers=world.org_a
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "date_to must not be before date_from"}


def test_pagination_total_and_pages(world: World) -> None:
    event_id = world.event(world.org_a)
    session_id = world.talk(world.org_a, event_id)
    for n in range(5):
        world.enroll(event_id, session_id, f"Person {n}")

    second = world.client.get(JSON_URL, params={"page": 2, "size": 2}, headers=world.org_a).json()

    assert len(second["items"]) == 2
    assert (second["total"], second["page"], second["size"], second["pages"]) == (5, 2, 2, 3)


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}])
def test_invalid_pagination_is_rejected(world: World, params: dict[str, int]) -> None:
    assert world.client.get(JSON_URL, params=params, headers=world.org_a).status_code == 422


def test_rows_are_ordered_by_session_start(world: World) -> None:
    event_id = world.event(world.org_a)
    later = world.talk(world.org_a, event_id, "Later", "2030-03-12T09:00:00Z")
    sooner = world.talk(world.org_a, event_id, "Sooner", "2030-03-11T09:00:00Z")
    world.enroll(event_id, later, "Ana Gomez")
    world.enroll(event_id, sooner, "Luis Perez")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert [item["session_title"] for item in body["items"]] == ["Sooner", "Later"]


def test_cancelled_enrollments_do_not_appear(world: World) -> None:
    event_id = world.event(world.org_a)
    session_id = world.talk(world.org_a, event_id)
    leaver = world.enroll(event_id, session_id, "Ana Gomez")
    world.enroll(event_id, session_id, "Luis Perez")
    world.client.delete(f"{EVENTS}/{event_id}/sessions/{session_id}/register", headers=leaver)

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert names(body) == ["Luis Perez"]


def test_csv_has_bom_header_semicolons_and_crlf(world: World) -> None:
    event_id = world.event(world.org_a, "PyCon")
    world.enroll(
        event_id,
        world.talk(world.org_a, event_id, "Keynote", "2030-03-10T09:00:00Z"),
        "Ana Gomez",
        "ana@example.com",
    )

    response = world.client.get(CSV_URL, headers=world.org_a)

    assert response.text == (
        f"{BOM}{HEADER}\r\nAna Gomez;ana@example.com;PyCon;Keynote;2030-03-10T09:00:00Z\r\n"
    )


def test_csv_neutralizes_formula_injection(world: World) -> None:
    event_id = world.event(world.org_a)
    session_id = world.talk(world.org_a, event_id, "=SUM(1+1)")
    world.enroll(event_id, session_id, "=cmd|' /C calc'!A0")

    rows = csv_rows(world.client.get(CSV_URL, headers=world.org_a).text)

    assert rows[1][0] == "'=cmd|' /C calc'!A0"
    assert rows[1][3] == "'=SUM(1+1)"


def test_csv_headers_for_a_dated_download(world: World) -> None:
    response = world.client.get(CSV_URL, headers=world.org_a)

    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    assert re.fullmatch(
        r'attachment; filename="participantes_sesiones_\d{8}\.csv"',
        response.headers["content-disposition"],
    )


def test_csv_filename_names_the_session_when_filtered(world: World) -> None:
    session_id = world.talk(world.org_a, world.event(world.org_a))

    response = world.client.get(CSV_URL, params={"session_id": session_id}, headers=world.org_a)

    assert response.headers["content-disposition"] == (
        f'attachment; filename="participantes_sesion_{session_id}.csv"'
    )


def test_csv_without_matches_has_only_the_header(world: World) -> None:
    response = world.client.get(CSV_URL, params={"q": "nothing"}, headers=world.org_a)

    assert response.status_code == 200
    assert response.text == f"{BOM}{HEADER}\r\n"


def test_json_and_csv_return_the_same_enrollments_for_the_same_filters(world: World) -> None:
    event_id = world.event(world.org_a, "PyCon Lima")
    other_event = world.event(world.org_b, "PyCon Quito")
    first = world.talk(world.org_a, event_id, "First", "2030-03-10T09:00:00Z")
    second = world.talk(world.org_a, event_id, "Second", "2030-03-20T09:00:00Z")
    foreign = world.talk(world.org_b, other_event, "Foreign", "2030-03-15T09:00:00Z")
    for n in range(3):
        world.enroll(event_id, first, f"First {n}")
        world.enroll(event_id, second, f"Second {n}")
        world.enroll(other_event, foreign, f"Foreign {n}")
    filters = {"q": "pycon", "status": "published", "date_from": "2030-03-05"}

    as_json = world.client.get(
        JSON_URL, params={**filters, "size": 100}, headers=world.admin
    ).json()
    as_csv = csv_rows(world.client.get(CSV_URL, params=filters, headers=world.admin).text)

    assert [
        [
            i["full_name"],
            i["email"],
            i["event_name"],
            i["session_title"],
            i["session_start"].replace("+00:00", "Z"),
        ]
        for i in as_json["items"]
    ] == as_csv[1:]
    assert len(as_csv) - 1 == as_json["total"] == 9


def test_session_reports_are_not_cached(world: World, fake_cache) -> None:  # type: ignore[no-untyped-def]
    world.client.get(CSV_URL, headers=world.org_a)
    world.client.get(JSON_URL, headers=world.org_a)

    assert fake_cache.sets == []


def test_openapi_documents_both_session_report_operations(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    preview = paths[JSON_URL]["get"]
    download = paths[CSV_URL]["get"]
    assert preview["tags"] == download["tags"] == ["reports"]
    assert set(download["responses"]["200"]["content"]) == {"text/csv"}
    for operation in (preview, download):
        assert {"401", "403", "404", "422"} <= set(operation["responses"])
