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


def conflict(description: str, detail: str) -> Responses:
    """409 for a request that clashes with the current state of the data."""
    return error_response(409, description, detail)
