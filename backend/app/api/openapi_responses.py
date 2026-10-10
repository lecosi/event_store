"""Reusable OpenAPI error responses, defined once and shared by every router.

Errors are always returned as ``{"detail": "<message>"}`` (FastAPI's ``HTTPException`` shape).
Request-validation failures (malformed body, wrong types) use FastAPI's standard 422 body,
where ``detail`` is a list of field errors; that default is intentionally left untouched.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Body of every error returned by the API."""

    detail: str = Field(
        description="Human-readable explanation of what went wrong.",
        examples=["Insufficient permissions"],
    )


Responses = dict[int | str, dict[str, Any]]


def error_response(status_code: int, description: str, detail: str) -> Responses:
    """Build one documented error entry (shared schema plus a concrete example body)."""
    return {
        status_code: {
            "model": ErrorResponse,
            "description": description,
            "content": {"application/json": {"example": {"detail": detail}}},
        }
    }


UNAUTHORIZED: Responses = error_response(
    401,
    "Missing, invalid or expired Bearer token, or the account is deactivated.",
    "Could not validate credentials",
)
FORBIDDEN: Responses = error_response(
    403,
    "The authenticated user's role (or ownership of the resource) does not allow this action.",
    "Insufficient permissions",
)


def not_found(what: str = "Resource") -> Responses:
    """404 for a missing (or, for events, not visible to the caller) resource."""
    return error_response(
        404, f"{what} does not exist or is not visible to the caller.", f"{what} not found"
    )


def conflict(description: str, detail: str) -> Responses:
    """409 for a request that clashes with the current state of the data."""
    return error_response(409, description, detail)


def combine(*parts: Responses) -> Responses:
    """Merge several response fragments; a later fragment wins on the same status code."""
    merged: Responses = {}
    for part in parts:
        merged.update(part)
    return merged


EVENT_NOT_FOUND = not_found("Event")
SESSION_NOT_FOUND = not_found("Session")
SPEAKER_NOT_FOUND = not_found("Speaker")
USER_NOT_FOUND = not_found("User")

# Typical combinations: authenticated-only, and organizer/admin-only endpoints.
AUTHENTICATED = combine(UNAUTHORIZED)
ORGANIZER_OR_ADMIN = combine(UNAUTHORIZED, FORBIDDEN)
