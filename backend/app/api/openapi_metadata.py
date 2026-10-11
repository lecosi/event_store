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

Endpoints marked with a lock require a token. Browsing events and speakers is public; a valid
token additionally reveals the caller's own non-published events and registration state.

## Roles

| Role | Can do |
| --- | --- |
| `attendee` | Browse published events, register/cancel, list own registrations. |
| `organizer` | Everything an attendee can, plus manage **own** events, sessions and speakers. |
| `admin` | Manage any event, and list users / change their role or active flag. |

The participants report (`GET /api/v1/reports/participants` and `.../participants.csv`) is
available to `organizer` (only the participants of their own events) and `admin` (all
events). Attendees receive `403`. Its `date_from` / `date_to` filter the event start date
in UTC, both days included.

## Errors

Errors use the shape `{"detail": "<message>"}` with these status codes: `401` (not
authenticated), `403` (role or ownership does not allow it), `404` (not found, or an
unpublished event hidden from the caller), `409` (conflicts with the current state, e.g. an
overlapping session, event full or email already registered) and `422` (invalid input; for
malformed bodies `detail` is a list of field errors, for business rules it is a message).

## Pagination

List endpoints accept `page` (1-based) and `size` (1-100, default 10) and return
`items`, `total`, `page`, `size` and `pages`.
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
    {
        "name": "events",
        "description": (
            "Event catalogue and lifecycle. Reading is public for `published` events; "
            "`draft`, `cancelled` and `finished` events are only visible to their organizer "
            "and admins. Writing requires `organizer` (own events) or `admin`."
        ),
    },
    {
        "name": "sessions",
        "description": (
            "Sessions (talks) scheduled inside an event. They must fit within the event dates, "
            "not exceed its capacity, and a speaker cannot have two overlapping sessions."
        ),
    },
    {
        "name": "admin",
        "description": "User administration. Restricted to the `admin` role.",
    },
    {
        "name": "registrations",
        "description": (
            "Attendee registration to events and the caller's registered events. "
            "Capacity is enforced atomically: the last spot is never oversold."
        ),
    },
    {
        "name": "reports",
        "description": (
            "Participants report: who is registered to which event, as a paginated preview "
            "and as a CSV download with the same filters. Restricted to `organizer` (own "
            "events) and `admin` (all events)."
        ),
    },
    {
        "name": "speakers",
        "description": (
            "Speaker directory, reusable across events. Reading is public; writing requires "
            "`organizer` or `admin`."
        ),
    },
]
