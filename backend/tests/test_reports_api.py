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

JSON_URL = "/api/v1/reports/participants"
CSV_URL = "/api/v1/reports/participants.csv"
BOM = "﻿"
HEADER = "Nombre completo;Correo electrónico;Evento"

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

    def event(
        self,
        owner: Headers,
        name: str = "PyCon",
        start_at: str = "2030-03-10T09:00:00Z",
        end_at: str | None = None,
        publish_it: bool = True,
        **fields: object,
    ) -> int:
        end = end_at or start_at.replace("T09", "T18")
        created = create(self.client, owner, name=name, start_at=start_at, end_at=end, **fields)
        if publish_it:
            publish(self.client, owner, created["id"])
        return created["id"]

    def join(self, event_id: int, full_name: str, email: str | None = None) -> Headers:
        self.counter += 1
        address = email or f"person{self.counter}@example.com"
        headers = make_user(self.client, self.session, address, Role.ATTENDEE)
        user = self.session.exec(select(User).where(User.email == address)).one()
        user.full_name = full_name
        self.session.add(user)
        self.session.commit()
        response = self.client.post(f"{EVENTS}/{event_id}/register", headers=headers)
        assert response.status_code == 201, response.text
        return headers


@pytest.fixture
def world(client: TestClient, session: Session) -> World:
    return World(
        client=client,
        session=session,
        org_a=make_user(client, session, "orga@example.com", Role.ORGANIZER),
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


def test_organizer_sees_only_participants_of_own_events(world: World) -> None:
    mine = world.event(world.org_a, "Mine")
    theirs = world.event(world.org_b, "Theirs")
    world.join(mine, "Ana Gomez", "ana@example.com")
    world.join(theirs, "Luis Perez", "luis@example.com")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert body["items"] == [
        {"full_name": "Ana Gomez", "email": "ana@example.com", "event_name": "Mine"}
    ]
    assert body["total"] == 1


def test_organizer_does_not_see_participants_of_foreign_published_events(world: World) -> None:
    world.join(world.event(world.org_b, "Theirs"), "Luis Perez")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert body["items"] == []


def test_admin_sees_participants_of_every_event(world: World) -> None:
    world.join(world.event(world.org_a, "Mine", "2030-03-10T09:00:00Z"), "Ana Gomez")
    world.join(world.event(world.org_b, "Theirs", "2030-03-11T09:00:00Z"), "Luis Perez")

    body = world.client.get(JSON_URL, headers=world.admin).json()

    assert names(body) == ["Ana Gomez", "Luis Perez"]


def test_foreign_event_id_is_forbidden_for_organizer(world: World) -> None:
    theirs = world.event(world.org_b)

    for url in (JSON_URL, CSV_URL):
        response = world.client.get(url, params={"event_id": theirs}, headers=world.org_a)
        assert response.status_code == 403
        assert response.json() == {"detail": "Insufficient permissions"}


def test_unknown_event_id_is_not_found(world: World) -> None:
    for url in (JSON_URL, CSV_URL):
        response = world.client.get(url, params={"event_id": 999}, headers=world.org_a)
        assert response.status_code == 404
        assert response.json() == {"detail": "Event not found"}


def test_admin_can_filter_by_any_event(world: World) -> None:
    theirs = world.event(world.org_b, "Theirs")
    other = world.event(world.org_a, "Other", "2030-03-11T09:00:00Z")
    world.join(theirs, "Luis Perez")
    world.join(other, "Ana Gomez")

    body = world.client.get(JSON_URL, params={"event_id": theirs}, headers=world.admin).json()

    assert names(body) == ["Luis Perez"]


def test_event_id_filter_limits_an_organizer_to_one_own_event(world: World) -> None:
    first = world.event(world.org_a, "First", "2030-03-10T09:00:00Z")
    second = world.event(world.org_a, "Second", "2030-03-11T09:00:00Z")
    world.join(first, "Ana Gomez")
    world.join(second, "Luis Perez")

    body = world.client.get(JSON_URL, params={"event_id": second}, headers=world.org_a).json()

    assert names(body) == ["Luis Perez"]


def test_event_without_participants_gives_an_empty_page(world: World) -> None:
    event_id = world.event(world.org_a)

    body = world.client.get(JSON_URL, params={"event_id": event_id}, headers=world.org_a).json()

    assert body == {"items": [], "total": 0, "page": 1, "size": 10, "pages": 0}


def test_q_matches_event_name_ignoring_case(world: World) -> None:
    world.join(world.event(world.org_a, "PyCon Latam", "2030-03-10T09:00:00Z"), "Ana Gomez")
    world.join(world.event(world.org_a, "JSConf", "2030-03-11T09:00:00Z"), "Luis Perez")

    body = world.client.get(JSON_URL, params={"q": "pycon"}, headers=world.org_a).json()

    assert names(body) == ["Ana Gomez"]


def test_q_does_not_search_participant_names(world: World) -> None:
    world.join(world.event(world.org_a, "PyCon"), "Ana Gomez")

    body = world.client.get(JSON_URL, params={"q": "Gomez"}, headers=world.org_a).json()

    assert body["items"] == []


def test_q_treats_like_wildcards_literally(world: World) -> None:
    world.join(world.event(world.org_a, "100% Python", "2030-03-10T09:00:00Z"), "Ana Gomez")
    world.join(world.event(world.org_a, "100 Python", "2030-03-11T09:00:00Z"), "Luis Perez")
    world.join(world.event(world.org_a, "a_b", "2030-03-12T09:00:00Z"), "Eva Ruiz")
    world.join(world.event(world.org_a, "axb", "2030-03-13T09:00:00Z"), "Raul Mora")

    percent = world.client.get(JSON_URL, params={"q": "%"}, headers=world.org_a).json()
    underscore = world.client.get(JSON_URL, params={"q": "a_b"}, headers=world.org_a).json()

    assert names(percent) == ["Ana Gomez"]
    assert names(underscore) == ["Eva Ruiz"]


def test_q_longer_than_200_characters_is_rejected(world: World) -> None:
    response = world.client.get(JSON_URL, params={"q": "x" * 201}, headers=world.org_a)

    assert response.status_code == 422


def test_status_filter(world: World) -> None:
    published = world.event(world.org_a, "Live", "2030-03-10T09:00:00Z")
    cancelled = world.event(world.org_a, "Soon Cancelled", "2030-03-12T09:00:00Z")
    world.join(published, "Ana Gomez")
    world.join(cancelled, "Luis Perez")
    world.client.patch(
        f"{EVENTS}/{cancelled}/status", json={"status": "cancelled"}, headers=world.org_a
    )

    live = world.client.get(JSON_URL, params={"status": "published"}, headers=world.org_a).json()
    gone = world.client.get(JSON_URL, params={"status": "cancelled"}, headers=world.org_a).json()
    drafts = world.client.get(JSON_URL, params={"status": "draft"}, headers=world.org_a).json()

    assert names(live) == ["Ana Gomez"]
    assert names(gone) == ["Luis Perez"]
    assert drafts["items"] == []


def test_invalid_status_is_rejected(world: World) -> None:
    response = world.client.get(JSON_URL, params={"status": "nope"}, headers=world.org_a)

    assert response.status_code == 422


def test_date_range_is_inclusive_in_utc(world: World) -> None:
    midnight = world.event(world.org_a, "Midnight", "2030-03-10T00:00:00Z", "2030-03-10T05:00:00Z")
    late = world.event(world.org_a, "Late", "2030-03-10T23:59:59Z", "2030-03-11T05:00:00Z")
    next_day = world.event(world.org_a, "Next", "2030-03-11T00:00:00Z", "2030-03-11T05:00:00Z")
    world.join(midnight, "Ana Gomez")
    world.join(late, "Luis Perez")
    world.join(next_day, "Eva Ruiz")

    day = world.client.get(
        JSON_URL,
        params={"date_from": "2030-03-10", "date_to": "2030-03-10"},
        headers=world.org_a,
    ).json()
    from_only = world.client.get(
        JSON_URL, params={"date_from": "2030-03-11"}, headers=world.org_a
    ).json()
    to_only = world.client.get(
        JSON_URL, params={"date_to": "2030-03-10"}, headers=world.org_a
    ).json()

    assert names(day) == ["Ana Gomez", "Luis Perez"]
    assert names(from_only) == ["Eva Ruiz"]
    assert names(to_only) == ["Ana Gomez", "Luis Perez"]


def test_date_to_before_date_from_is_unprocessable(world: World) -> None:
    params = {"date_from": "2030-03-11", "date_to": "2030-03-10"}

    for url in (JSON_URL, CSV_URL):
        response = world.client.get(url, params=params, headers=world.org_a)
        assert response.status_code == 422
        assert response.json() == {"detail": "date_to must not be before date_from"}


def test_malformed_date_is_unprocessable(world: World) -> None:
    response = world.client.get(JSON_URL, params={"date_from": "soon"}, headers=world.org_a)

    assert response.status_code == 422


def test_pagination_total_and_pages(world: World) -> None:
    event_id = world.event(world.org_a, capacity=10)
    for n in range(5):
        world.join(event_id, f"Person {n}")

    second = world.client.get(JSON_URL, params={"page": 2, "size": 2}, headers=world.org_a).json()
    last = world.client.get(JSON_URL, params={"page": 3, "size": 2}, headers=world.org_a).json()
    beyond = world.client.get(JSON_URL, params={"page": 4, "size": 2}, headers=world.org_a).json()

    assert names(second) == ["Person 2", "Person 3"]
    assert (second["total"], second["page"], second["size"], second["pages"]) == (5, 2, 2, 3)
    assert names(last) == ["Person 4"]
    assert beyond["items"] == []
    assert beyond["total"] == 5


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}])
def test_invalid_pagination_is_rejected(world: World, params: dict[str, int]) -> None:
    assert world.client.get(JSON_URL, params=params, headers=world.org_a).status_code == 422


def test_rows_are_ordered_by_event_start_then_registration(world: World) -> None:
    later = world.event(world.org_a, "Later", "2030-04-01T09:00:00Z")
    sooner = world.event(world.org_a, "Sooner", "2030-03-01T09:00:00Z")
    world.join(later, "Zoe First")
    world.join(sooner, "Yan Second")
    world.join(sooner, "Abe Third")

    body = world.client.get(JSON_URL, headers=world.org_a).json()

    assert [(i["event_name"], i["full_name"]) for i in body["items"]] == [
        ("Sooner", "Yan Second"),
        ("Sooner", "Abe Third"),
        ("Later", "Zoe First"),
    ]


def test_cancelled_registrations_do_not_appear(world: World) -> None:
    event_id = world.event(world.org_a)
    leaving = world.join(event_id, "Ana Gomez")
    world.join(event_id, "Luis Perez")
    world.client.delete(f"{EVENTS}/{event_id}/register", headers=leaving)

    json_body = world.client.get(JSON_URL, headers=world.org_a).json()
    csv_body = csv_rows(world.client.get(CSV_URL, headers=world.org_a).text)

    assert names(json_body) == ["Luis Perez"]
    assert [row[0] for row in csv_body[1:]] == ["Luis Perez"]


def test_csv_has_bom_header_semicolons_and_crlf(world: World) -> None:
    event_id = world.event(world.org_a, "Charla de Pérez")
    world.join(event_id, "José Peña", "jose@example.com")

    response = world.client.get(CSV_URL, headers=world.org_a)

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.text == (f"{BOM}{HEADER}\r\nJosé Peña;jose@example.com;Charla de Pérez\r\n")


def test_csv_quotes_values_with_separator_or_quotes(world: World) -> None:
    event_id = world.event(world.org_a, "Charlas; talleres")
    world.join(event_id, 'Ana "La Jefa" Gomez', "ana@example.com")

    response = world.client.get(CSV_URL, headers=world.org_a)

    assert response.text.endswith('"Ana ""La Jefa"" Gomez";ana@example.com;"Charlas; talleres"\r\n')
    assert csv_rows(response.text)[1] == [
        'Ana "La Jefa" Gomez',
        "ana@example.com",
        "Charlas; talleres",
    ]


def test_csv_neutralizes_formula_injection(world: World) -> None:
    event_id = world.event(world.org_a, "=SUM(1+1)")
    world.join(event_id, '=HYPERLINK("http://evil")', "a@example.com")
    world.join(event_id, "+cmd", "b@example.com")
    world.join(event_id, "-cmd", "c@example.com")
    world.join(event_id, "@cmd", "d@example.com")

    rows = csv_rows(world.client.get(CSV_URL, headers=world.org_a).text)

    assert [row[0] for row in rows[1:]] == [
        '\'=HYPERLINK("http://evil")',
        "'+cmd",
        "'-cmd",
        "'@cmd",
    ]
    assert {row[2] for row in rows[1:]} == {"'=SUM(1+1)"}


def test_csv_headers_for_a_dated_download(world: World) -> None:
    response = world.client.get(CSV_URL, headers=world.org_a)

    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    assert re.fullmatch(
        r'attachment; filename="participantes_\d{8}\.csv"',
        response.headers["content-disposition"],
    )


def test_csv_filename_names_the_event_when_filtered(world: World) -> None:
    event_id = world.event(world.org_a)

    response = world.client.get(CSV_URL, params={"event_id": event_id}, headers=world.org_a)

    assert response.headers["content-disposition"] == (
        f'attachment; filename="participantes_evento_{event_id}.csv"'
    )


def test_csv_without_matches_has_only_the_header(world: World) -> None:
    response = world.client.get(CSV_URL, params={"q": "nothing"}, headers=world.org_a)

    assert response.status_code == 200
    assert response.text == f"{BOM}{HEADER}\r\n"


def test_json_and_csv_return_the_same_participants_for_the_same_filters(world: World) -> None:
    first = world.event(world.org_a, "PyCon Lima", "2030-03-10T09:00:00Z")
    second = world.event(world.org_a, "PyCon Cusco", "2030-03-20T09:00:00Z")
    world.event(world.org_b, "PyCon Quito", "2030-03-15T09:00:00Z")
    for n in range(3):
        world.join(first, f"Lima {n}")
        world.join(second, f"Cusco {n}")
    filters = {"q": "pycon", "status": "published", "date_from": "2030-03-05"}

    as_json = world.client.get(
        JSON_URL, params={**filters, "size": 100}, headers=world.admin
    ).json()
    as_csv = csv_rows(world.client.get(CSV_URL, params=filters, headers=world.admin).text)

    assert [[i["full_name"], i["email"], i["event_name"]] for i in as_json["items"]] == as_csv[1:]
    assert as_csv[0] == ["Nombre completo", "Correo electrónico", "Evento"]
    assert len(as_csv) - 1 == as_json["total"] == 6


def test_csv_is_not_cached(world: World, fake_cache) -> None:  # type: ignore[no-untyped-def]
    world.client.get(CSV_URL, headers=world.org_a)
    world.client.get(JSON_URL, headers=world.org_a)

    assert fake_cache.sets == []


def test_openapi_documents_both_report_operations(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    preview = paths[JSON_URL]["get"]
    download = paths[CSV_URL]["get"]
    assert preview["tags"] == download["tags"] == ["reports"]
    assert set(download["responses"]["200"]["content"]) == {"text/csv"}
    for operation in (preview, download):
        assert {"401", "403", "404", "422"} <= set(operation["responses"])
