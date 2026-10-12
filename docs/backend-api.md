# Backend API

REST API under the prefix `/api/v1`, JSON in and out. The router modules are in
`backend/app/api/v1`; request and response schemas are in `backend/app/api`.

## Interactive documentation

FastAPI serves the generated OpenAPI with the default paths:

| Path | What |
| --- | --- |
| `/docs` | Swagger UI (use **Authorize** with a token from `/api/v1/auth/login`) |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI document |

With the docker compose setup these are at `http://localhost:8000/docs` and so on.
Every operation has a summary, a description and documented error responses, so this page
is only an overview.

## Authentication

1. `POST /api/v1/auth/login` with email and password returns `{"access_token": "<jwt>"}`.
2. Send `Authorization: Bearer <token>` on protected endpoints.

Tokens are JWT (`HS256` by default) and expire after `ACCESS_TOKEN_EXPIRE_MINUTES`
(default 60). Endpoints marked "optional" accept a token but also work anonymously; an
invalid token there is treated as anonymous, never as an error.

## Conventions

### Errors

Every error body has the same shape:

```json
{ "detail": "Event not found" }
```

| Status | Meaning |
| --- | --- |
| 401 | Missing or invalid token, or wrong credentials |
| 403 | Authenticated but not allowed (role or ownership) |
| 404 | Resource missing, or not visible to the caller (draft events look missing) |
| 409 | Conflict with the current state: full, duplicate, overlap, invalid transition |
| 422 | Invalid input |

Domain errors are mapped in `app/api/error_handlers.py` (see
[backend-architecture.md](backend-architecture.md)). Request-shape validation errors from
FastAPI/Pydantic also answer 422, but `detail` is then a list of objects
(`loc`, `msg`, `type`) instead of a string.

### Pagination

List endpoints take `page` (1-based, default 1) and `size` (1 to 100, default 10) and
return:

```json
{ "items": [], "total": 25, "page": 1, "size": 10, "pages": 3 }
```

`pages` is `0` when there are no results. Out-of-range `page` or `size` answers 422.

### Dates and CORS

Datetimes are ISO 8601; naive values are treated as UTC. Report date filters are plain
`YYYY-MM-DD` UTC days. Allowed browser origins come from `CORS_ORIGINS`; the
`Content-Disposition` header is exposed so the frontend can name CSV downloads.

## Endpoints

Role legend: **public** (no token), **optional** (token changes the result), **any**
(any authenticated user), **organizer** (organizer or admin, plus ownership where noted),
**admin**.

### health

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | public | Liveness check, returns `{"status": "ok"}` |

### auth

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | public | Create an account (always `organizer`) |
| POST | `/api/v1/auth/login` | public | Exchange credentials for an access token |
| GET | `/api/v1/users/me` | any | Profile of the authenticated user |

### events

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/events` | organizer | Create an event (starts as `draft`) |
| GET | `/api/v1/events` | optional | Search and paginate events (`q`, `status`, `page`, `size`) |
| GET | `/api/v1/events/{event_id}` | optional | Event detail with sessions, registered count and availability |
| PUT | `/api/v1/events/{event_id}` | organizer, owner | Replace the editable fields |
| PATCH | `/api/v1/events/{event_id}/status` | organizer, owner | Change status along the allowed transitions |
| DELETE | `/api/v1/events/{event_id}` | organizer, owner | Delete the event and its dependents |

"Owner" means the event's organizer; admins can manage any event.

### sessions

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/events/{event_id}/sessions` | optional | Sessions with speaker, seats left and the caller's enrollment |
| POST | `/api/v1/events/{event_id}/sessions` | organizer, owner | Schedule a session |
| PUT | `/api/v1/events/{event_id}/sessions/{session_id}` | organizer, owner | Replace a session |
| DELETE | `/api/v1/events/{event_id}/sessions/{session_id}` | organizer, owner | Remove a session (409 if it has enrollments) |

### speakers

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/speakers` | organizer | Add a speaker to the shared directory |
| GET | `/api/v1/speakers` | public | Paginated directory, optional `q` on the name |
| GET | `/api/v1/speakers/{speaker_id}` | public | One speaker |
| PUT | `/api/v1/speakers/{speaker_id}` | organizer | Replace a speaker |
| DELETE | `/api/v1/speakers/{speaker_id}` | organizer | Delete (409 if it has sessions) |

### registrations

Registration to an event and enrollment in a session. All require a token (any role).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/events/{event_id}/register` | Register to an event |
| DELETE | `/api/v1/events/{event_id}/register` | Cancel the registration (also cancels its session enrollments) |
| GET | `/api/v1/users/me/events` | Paginated events the caller is registered to |
| POST | `/api/v1/events/{event_id}/sessions/{session_id}/register` | Enroll in a session |
| DELETE | `/api/v1/events/{event_id}/sessions/{session_id}/register` | Cancel the enrollment |

### reports

Role: organizer or admin. Organizers only see their own events. Filters: `event_id`, `q`,
`status`, `date_from`, `date_to` (and `session_id` for the session reports).

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/reports/participants` | Paginated preview of registered people |
| GET | `/api/v1/reports/participants.csv` | Same filters, whole result as a CSV download |
| GET | `/api/v1/reports/sessions/participants` | Paginated preview of enrolled people |
| GET | `/api/v1/reports/sessions/participants.csv` | Same filters, whole result as a CSV download |

CSV format and file names are described in
[backend-domain-rules.md](backend-domain-rules.md#reports-and-csv).

### admin

Role: admin.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | Paginated users, optional `email` prefix search |
| PATCH | `/api/v1/admin/users/{user_id}` | Partial update of name, email, role or active flag |

## Keeping this page accurate

The tables above were checked against the generated OpenAPI. To list the real endpoints
again:

```bash
cd backend   # JWT_SECRET must be set, see backend-operations.md
poetry run python -c "from app.main import app; \
[print(m.upper(), p) for p, ms in app.openapi()['paths'].items() for m in ms]"
```

`backend/tests/test_router_structure.py` and the `test_*_api.py` files document the
behavior of each endpoint through tests.
