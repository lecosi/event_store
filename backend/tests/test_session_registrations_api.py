from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, select

from app.application.ports import SESSIONS_NAMESPACE
from app.domain.enums import Role
from app.infrastructure.db.models import SessionRegistration
from tests.fakes import FakeCache
from tests.test_events_api import EVENTS, make_user, organizer, publish
from tests.test_registrations_api import register
from tests.test_sessions_api import make_event, make_speaker, session_body, url


def attendee(client: TestClient, session: Session, n: int) -> dict[str, str]:
    return make_user(client, session, f"att{n}@example.com", Role.ATTENDEE)


def enroll_url(event_id: int, session_id: int) -> str:
    return f"{url(event_id, session_id)}/register"


def enroll(client: TestClient, headers: dict[str, str], event_id: int, session_id: int) -> Response:
    return client.post(enroll_url(event_id, session_id), headers=headers)


def add_session(
    client: TestClient,
    headers: dict[str, str],
    event_id: int,
    speaker_id: int,
    **fields: object,
) -> int:
    response = client.post(url(event_id), json=session_body(speaker_id, **fields), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def published_event_with_session(
    client: TestClient, session: Session, **session_fields: object
) -> tuple[dict[str, str], int, int]:
    headers = organizer(client, session)
    event = make_event(client, headers)
    publish(client, headers, event["id"])
    speaker = make_speaker(client, headers)
    session_id = add_session(client, headers, event["id"], speaker["id"], **session_fields)
    return headers, event["id"], session_id


def registered_attendee(
    client: TestClient, session: Session, n: int, event_id: int
) -> dict[str, str]:
    headers = attendee(client, session, n)
    assert register(client, headers, event_id).status_code == 201
    return headers


def listed(client: TestClient, event_id: int, headers: dict[str, str] | None = None) -> dict:
    response = client.get(url(event_id), headers=headers or {})
    assert response.status_code == 200, response.text
    return response.json()[0]


def test_enrolling_requires_authentication(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    assert client.post(enroll_url(event_id, session_id)).status_code == 401
    assert client.delete(enroll_url(event_id, session_id)).status_code == 401


def test_registered_attendee_can_enroll_in_a_session(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    response = enroll(client, headers, event_id, session_id)
    assert response.status_code == 201
    assert response.json()["session_id"] == session_id


def test_session_full_rejects_the_next_attendee(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session, capacity=1)
    first = registered_attendee(client, session, 1, event_id)
    second = registered_attendee(client, session, 2, event_id)
    assert enroll(client, first, event_id, session_id).status_code == 201
    response = enroll(client, second, event_id, session_id)
    assert response.status_code == 409
    assert "full" in response.json()["detail"]


def test_duplicate_enrollment_is_conflict(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    assert enroll(client, headers, event_id, session_id).status_code == 201
    assert enroll(client, headers, event_id, session_id).status_code == 409


def test_enrollment_requires_the_event_registration(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    response = enroll(client, attendee(client, session, 1), event_id, session_id)
    assert response.status_code == 409
    assert "Register to the event" in response.json()["detail"]


def test_enrolling_in_a_draft_event_session_is_not_found(
    client: TestClient, session: Session
) -> None:
    headers = organizer(client, session)
    event = make_event(client, headers)
    speaker = make_speaker(client, headers)
    session_id = add_session(client, headers, event["id"], speaker["id"])
    other = attendee(client, session, 1)
    assert enroll(client, other, event["id"], session_id).status_code == 404


def test_enrolling_in_a_cancelled_event_session_is_rejected(
    client: TestClient, session: Session
) -> None:
    owner, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    client.patch(f"{EVENTS}/{event_id}/status", json={"status": "cancelled"}, headers=owner)
    assert enroll(client, headers, event_id, session_id).status_code == 404
    assert enroll(client, owner, event_id, session_id).status_code == 409


def test_session_of_another_event_is_not_found(client: TestClient, session: Session) -> None:
    owner, event_id, _ = published_event_with_session(client, session)
    other_event = make_event(client, owner)
    publish(client, owner, other_event["id"])
    speaker = make_speaker(client, owner, name="Grace")
    foreign = add_session(client, owner, other_event["id"], speaker["id"])
    headers = registered_attendee(client, session, 1, event_id)
    assert enroll(client, headers, event_id, foreign).status_code == 404


def test_overlapping_sessions_of_the_same_event_are_rejected(
    client: TestClient, session: Session
) -> None:
    owner, event_id, first = published_event_with_session(client, session, start=1, end=3)
    other_speaker = make_speaker(client, owner, name="Grace")
    second = add_session(client, owner, event_id, other_speaker["id"], start=2, end=4)
    headers = registered_attendee(client, session, 1, event_id)
    assert enroll(client, headers, event_id, first).status_code == 201
    response = enroll(client, headers, event_id, second)
    assert response.status_code == 409
    assert "overlaps" in response.json()["detail"]


def test_overlapping_session_of_another_event_is_rejected(
    client: TestClient, session: Session
) -> None:
    owner, event_id, first = published_event_with_session(client, session, start=1, end=3)
    other_event = make_event(client, owner)
    publish(client, owner, other_event["id"])
    other_speaker = make_speaker(client, owner, name="Grace")
    second = add_session(client, owner, other_event["id"], other_speaker["id"], start=2, end=4)
    headers = registered_attendee(client, session, 1, event_id)
    assert register(client, headers, other_event["id"]).status_code == 201
    assert enroll(client, headers, event_id, first).status_code == 201
    assert enroll(client, headers, other_event["id"], second).status_code == 409


def test_non_overlapping_sessions_of_one_event_are_all_allowed(
    client: TestClient, session: Session
) -> None:
    owner, event_id, first = published_event_with_session(client, session, start=1, end=2)
    speaker = make_speaker(client, owner, name="Grace")
    second = add_session(client, owner, event_id, speaker["id"], start=2, end=3)
    third = add_session(client, owner, event_id, speaker["id"], start=4, end=5)
    headers = registered_attendee(client, session, 1, event_id)
    for session_id in (first, second, third):
        assert enroll(client, headers, event_id, session_id).status_code == 201


def test_cancelling_an_enrollment_frees_the_seat(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session, capacity=1)
    first = registered_attendee(client, session, 1, event_id)
    second = registered_attendee(client, session, 2, event_id)
    enroll(client, first, event_id, session_id)
    assert client.delete(enroll_url(event_id, session_id), headers=first).status_code == 204
    assert enroll(client, second, event_id, session_id).status_code == 201


def test_cancelling_without_enrollment_is_not_found(client: TestClient, session: Session) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    assert client.delete(enroll_url(event_id, session_id), headers=headers).status_code == 404


def test_cancelling_is_rejected_once_the_event_is_finished(
    client: TestClient, session: Session
) -> None:
    owner, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    client.patch(f"{EVENTS}/{event_id}/status", json={"status": "finished"}, headers=owner)
    assert client.delete(enroll_url(event_id, session_id), headers=headers).status_code == 409


def test_cancelling_the_event_registration_removes_its_session_enrollments(
    client: TestClient, session: Session
) -> None:
    _, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    assert client.delete(f"{EVENTS}/{event_id}/register", headers=headers).status_code == 204
    assert session.exec(select(SessionRegistration)).all() == []


def test_deleting_a_session_removes_its_enrollments(client: TestClient, session: Session) -> None:
    owner, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    assert client.delete(url(event_id, session_id), headers=owner).status_code == 204
    assert session.exec(select(SessionRegistration)).all() == []


def test_deleting_an_event_removes_its_session_enrollments(
    client: TestClient, session: Session
) -> None:
    owner, event_id, session_id = published_event_with_session(client, session)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    client.patch(f"{EVENTS}/{event_id}/status", json={"status": "cancelled"}, headers=owner)
    assert client.delete(f"{EVENTS}/{event_id}", headers=owner).status_code == 204
    assert session.exec(select(SessionRegistration)).all() == []


def test_session_listing_reports_availability_for_the_caller(
    client: TestClient, session: Session
) -> None:
    _, event_id, session_id = published_event_with_session(client, session, capacity=3)
    first = registered_attendee(client, session, 1, event_id)
    second = registered_attendee(client, session, 2, event_id)
    enroll(client, first, event_id, session_id)
    mine = listed(client, event_id, first)
    other = listed(client, event_id, second)
    anonymous = listed(client, event_id)
    assert (mine["enrolled_count"], mine["available_spots"], mine["is_enrolled"]) == (1, 2, True)
    assert (other["enrolled_count"], other["is_enrolled"]) == (1, False)
    assert (anonymous["enrolled_count"], anonymous["is_enrolled"]) == (1, False)


def test_event_detail_sessions_report_availability_for_the_caller(
    client: TestClient, session: Session
) -> None:
    _, event_id, session_id = published_event_with_session(client, session, capacity=3)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    detail = client.get(f"{EVENTS}/{event_id}", headers=headers).json()["sessions"][0]
    assert (detail["enrolled_count"], detail["available_spots"], detail["is_enrolled"]) == (
        1,
        2,
        True,
    )


def test_session_update_response_reports_current_availability(
    client: TestClient, session: Session
) -> None:
    owner, event_id, session_id = published_event_with_session(client, session, capacity=3)
    headers = registered_attendee(client, session, 1, event_id)
    enroll(client, headers, event_id, session_id)
    speaker_id = listed(client, event_id)["speaker"]["id"]
    updated = client.put(
        url(event_id, session_id),
        json=session_body(speaker_id, capacity=5),
        headers=owner,
    ).json()
    assert (updated["enrolled_count"], updated["available_spots"]) == (1, 4)


def test_created_session_starts_with_all_its_seats_available(
    client: TestClient, session: Session
) -> None:
    owner = organizer(client, session)
    event = make_event(client, owner)
    speaker = make_speaker(client, owner)
    created = client.post(
        url(event["id"]), json=session_body(speaker["id"], capacity=7), headers=owner
    ).json()
    assert (created["enrolled_count"], created["available_spots"]) == (0, 7)


def test_cached_session_listing_never_serves_stale_or_foreign_enrollment_data(
    client: TestClient, session: Session, fake_cache: FakeCache
) -> None:
    _, event_id, session_id = published_event_with_session(client, session, capacity=3)
    first = registered_attendee(client, session, 1, event_id)
    second = registered_attendee(client, session, 2, event_id)
    assert listed(client, event_id, second)["enrolled_count"] == 0
    enroll(client, first, event_id, session_id)
    as_first = listed(client, event_id, first)
    as_second = listed(client, event_id, second)
    assert (as_first["enrolled_count"], as_first["is_enrolled"]) == (1, True)
    assert (as_second["enrolled_count"], as_second["is_enrolled"]) == (1, False)
    cached = [value for ns, _, value, _ in fake_cache.sets if ns == SESSIONS_NAMESPACE]
    assert cached
    assert all("is_enrolled" not in value and "enrolled_count" not in value for value in cached)
