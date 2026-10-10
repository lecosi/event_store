"""Top-level OpenAPI metadata: API description and per-tag documentation."""

API_DESCRIPTION = """\
REST API of **Mis Eventos**, an event management platform. Organizers publish events with
sessions and speakers; attendees browse, search and register until the capacity is reached.

## Authentication flow

1. `POST /api/v1/auth/register` creates an account (always with the `organizer` role, so it
   can create events right away).
2. `POST /api/v1/auth/login` returns an `access_token` (JWT).
3. Click **Authorize** (top right) and paste the token. Swagger sends it as
   `Authorization: Bearer <token>` on every request.

Endpoints marked with a lock require a token.

## Roles

| Role | Can do |
| --- | --- |
| `attendee` | Browse published events, register/cancel, list own registrations. |
| `organizer` | Everything an attendee can, plus manage **own** events, sessions and speakers. |
| `admin` | Manage any event, and list users / change their role or active flag. |

## Errors

Errors use the shape `{"detail": "<message>"}` with these status codes: `401` (not
authenticated), `403` (role or ownership does not allow it), `409` (conflicts with the current
state, e.g. email already registered) and `422` (invalid input; for malformed bodies `detail`
is a list of field errors, for business rules it is a message).
"""

TAGS_METADATA = [
    {
        "name": "health",
        "description": "Liveness probe used by Docker and load balancers.",
    },
    {
        "name": "auth",
        "description": "Account registration, login (JWT) and the current user profile.",
    },
]
