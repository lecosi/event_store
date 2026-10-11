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


class ValidationErrorItem(BaseModel):
    """One invalid field reported by request validation."""

    loc: list[str | int] = Field(
        description="Path to the invalid value.", examples=[["body", "email"]]
    )
    msg: str = Field(
        description="What is wrong with the value.", examples=["value is not a valid email address"]
    )
    type: str = Field(description="Machine-readable error type.", examples=["value_error"])


class ValidationErrorResponse(BaseModel):
    """Body of a 422 returned when the request does not pass validation."""

    detail: list[ValidationErrorItem] = Field(description="Every invalid field of the request.")


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


def error_examples(
    status_code: int, description: str, examples: dict[str, tuple[str, str]]
) -> Responses:
    """Build one documented error entry with several named example bodies.

    ``examples`` maps an example name to ``(summary, detail)``.
    """
    return {
        status_code: {
            "model": ErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "examples": {
                        name: {"summary": summary, "value": {"detail": detail}}
                        for name, (summary, detail) in examples.items()
                    }
                }
            },
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


def validation_error(description: str, loc: list[str | int], msg: str, kind: str) -> Responses:
    """422 for a request body or parameter that fails validation (FastAPI's list-of-errors body)."""
    return {
        422: {
            "model": ValidationErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "example": {"detail": [{"loc": loc, "msg": msg, "type": kind}]}
                }
            },
        }
    }


def conflict(description: str, detail: str) -> Responses:
    """409 for a request that clashes with the current state of the data."""
    return error_response(409, description, detail)


def conflicts(description: str, examples: dict[str, tuple[str, str]]) -> Responses:
    """409 documented with several named causes, each with its own ``detail`` text."""
    return error_examples(409, description, examples)


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
