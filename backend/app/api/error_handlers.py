from dataclasses import dataclass

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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
from app.domain.registration import NotRegisteredError, RegistrationConflictError
from app.domain.session import SessionConflictError, SessionValidationError

SELF_LOCKOUT_DETAIL = "Admins cannot demote or deactivate their own account"


@dataclass(frozen=True)
class ErrorResponse:
    """HTTP status plus a fixed detail; ``detail=None`` exposes the exception message."""

    status_code: int
    detail: str | None = None
    headers: dict[str, str] | None = None


ERROR_RESPONSES: dict[type[Exception], ErrorResponse] = {
    EventNotFoundError: ErrorResponse(status.HTTP_404_NOT_FOUND, "Event not found"),
    SessionNotFoundError: ErrorResponse(status.HTTP_404_NOT_FOUND, "Session not found"),
    SpeakerNotFoundError: ErrorResponse(status.HTTP_404_NOT_FOUND, "Speaker not found"),
    UserNotFoundError: ErrorResponse(status.HTTP_404_NOT_FOUND, "User not found"),
    NotRegisteredError: ErrorResponse(status.HTTP_404_NOT_FOUND, "You are not registered"),
    PermissionDeniedError: ErrorResponse(status.HTTP_403_FORBIDDEN, "Insufficient permissions"),
    EventValidationError: ErrorResponse(status.HTTP_422_UNPROCESSABLE_ENTITY),
    SessionValidationError: ErrorResponse(status.HTTP_422_UNPROCESSABLE_ENTITY),
    EventStateError: ErrorResponse(status.HTTP_409_CONFLICT),
    SessionConflictError: ErrorResponse(status.HTTP_409_CONFLICT),
    RegistrationConflictError: ErrorResponse(status.HTTP_409_CONFLICT),
    EmailAlreadyRegisteredError: ErrorResponse(
        status.HTTP_409_CONFLICT, "Email already registered"
    ),
    SpeakerEmailTakenError: ErrorResponse(status.HTTP_409_CONFLICT, "Speaker email already in use"),
    SpeakerInUseError: ErrorResponse(
        status.HTTP_409_CONFLICT, "Speaker has sessions and cannot be deleted"
    ),
    SelfLockoutError: ErrorResponse(status.HTTP_409_CONFLICT, SELF_LOCKOUT_DETAIL),
    InvalidCredentialsError: ErrorResponse(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid email or password",
        {"WWW-Authenticate": "Bearer"},
    ),
}


def _handle(_: Request, exc: Exception) -> JSONResponse:
    # Starlette resolves handlers through the exception's MRO, so subclasses of a mapped
    # class always find an entry here.
    mapping = next(ERROR_RESPONSES[cls] for cls in type(exc).__mro__ if cls in ERROR_RESPONSES)
    detail = mapping.detail if mapping.detail is not None else str(exc)
    return JSONResponse({"detail": detail}, mapping.status_code, mapping.headers)


def register_exception_handlers(app: FastAPI) -> None:
    for error_type in ERROR_RESPONSES:
        app.add_exception_handler(error_type, _handle)
