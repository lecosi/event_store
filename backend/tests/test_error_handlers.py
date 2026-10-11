import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.errors import (
    EmailAlreadyRegisteredError,
    EventNotFoundError,
    InvalidCredentialsError,
    PermissionDeniedError,
    SelfLockoutError,
    SessionNotFoundError,
    SpeakerEmailTakenError,
    SpeakerInUseError,
    SpeakerNotFoundError,
    UserNotFoundError,
)
from app.domain.event import EventStateError, EventValidationError
from app.domain.registration import (
    AlreadyRegisteredError,
    EventFullError,
    NotRegisteredError,
    RegistrationClosedError,
)
from app.domain.session import SessionConflictError, SessionValidationError
from app.main import create_app

EXPECTED = [
    (EventNotFoundError(), 404, "Event not found"),
    (SessionNotFoundError(), 404, "Session not found"),
    (SpeakerNotFoundError(), 404, "Speaker not found"),
    (UserNotFoundError(), 404, "User not found"),
    (NotRegisteredError(), 404, "You are not registered"),
    (PermissionDeniedError(), 403, "Insufficient permissions"),
    (EventValidationError("bad dates"), 422, "bad dates"),
    (SessionValidationError("bad slot"), 422, "bad slot"),
    (EventStateError("event is closed"), 409, "event is closed"),
    (SessionConflictError("speaker busy"), 409, "speaker busy"),
    (AlreadyRegisteredError("already in"), 409, "already in"),
    (EventFullError("no spots"), 409, "no spots"),
    (RegistrationClosedError("closed"), 409, "closed"),
    (EmailAlreadyRegisteredError(), 409, "Email already registered"),
    (SpeakerEmailTakenError(), 409, "Speaker email already in use"),
    (SpeakerInUseError(), 409, "Speaker has sessions and cannot be deleted"),
    (SelfLockoutError(), 409, "Admins cannot demote or deactivate their own account"),
    (InvalidCredentialsError(), 401, "Invalid email or password"),
]


@pytest.fixture
def raising_app() -> FastAPI:
    app = create_app()
    state: dict[str, Exception] = {}

    @app.get("/_raise")
    def _raise() -> None:
        raise state["error"]

    app.state.raise_state = state
    return app


@pytest.fixture
def raising_client(raising_app: FastAPI) -> TestClient:
    return TestClient(raising_app, raise_server_exceptions=False)


def _trigger(client: TestClient, error: Exception):
    client.app.state.raise_state["error"] = error
    return client.get("/_raise")


@pytest.mark.parametrize(
    ("error", "status_code", "detail"), EXPECTED, ids=[type(e[0]).__name__ for e in EXPECTED]
)
def test_mapped_error_produces_its_status_and_detail(raising_client, error, status_code, detail):
    response = _trigger(raising_client, error)

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


def test_invalid_credentials_error_advertises_bearer_challenge(raising_client):
    response = _trigger(raising_client, InvalidCredentialsError())

    assert response.headers["www-authenticate"] == "Bearer"


def test_unmapped_exception_surfaces_as_internal_server_error(raising_client):
    response = _trigger(raising_client, RuntimeError("boom"))

    assert response.status_code == 500


def test_unmapped_exception_is_not_reported_as_handled_error_detail(raising_client):
    response = _trigger(raising_client, RuntimeError("boom"))

    assert "boom" not in response.text
