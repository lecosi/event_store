# Backend cache

An optional Redis read cache accelerates the public read endpoints. It never holds the
source of truth, never stores viewer-specific data and the API behaves the same without it.

Code map:

| Concern | File |
| --- | --- |
| `Cache` port, namespace names | `backend/app/application/ports.py` |
| Keys, TTLs and invalidation per aggregate | `backend/app/application/cache_policy.py` |
| Cached decorators of the read use cases | `backend/app/infrastructure/cache/cached_readers.py` |
| Read-through helper | `backend/app/infrastructure/cache/read_through.py` |
| Redis adapter | `backend/app/infrastructure/cache/redis_cache.py` |
| No-op adapter | `backend/app/infrastructure/cache/null_cache.py` |
| Wiring | `get_cache`, `get_*_cache` in `backend/app/api/dependencies.py` |

## What is cached

| Namespace | Cached read | Key (inside the namespace) | TTL setting (default) |
| --- | --- | --- | --- |
| `events` | Public event list pages | `list:<sha256(q)\|->:<status\|any>:<page>:<size>` | `CACHE_TTL_EVENTS_SECONDS` (60) |
| `sessions` | Schedule of one event (sessions with speaker name) | `event:<event_id>` | `CACHE_TTL_SESSIONS_SECONDS` (120) |
| `speakers` | Directory page | `list:<sha256(q)\|->:<page>:<size>` | `CACHE_TTL_SPEAKERS_SECONDS` (300) |
| `speakers` | One speaker | `detail:<speaker_id>` | `CACHE_TTL_SPEAKERS_SECONDS` (300) |

Search text enters keys only as a SHA-256 digest (`text_digest`), so user input never
becomes a raw key. TTLs must be greater than zero (`Settings` validation).

### What is deliberately not cached

- The event list for organizers and admins: they see non-published events, so only
  anonymous users and attendees (`is_public_view`) share the cached public view.
- Event detail (`GET /events/{id}`), "my events" and the reports.
- Per-viewer availability of sessions (`enrolled_count`, `available_spots`, `is_enrolled`):
  `SessionCatalogue` merges the cached schedule with live counts on every request, so
  registering or enrolling never needs to invalidate anything.

## Invalidation

Invalidation is explicit and always runs after the transaction commits, so a rollback
leaves the cache untouched.

| Operation | Namespaces dropped |
| --- | --- |
| Create, update or change status of an event | `events` |
| Delete an event | `events`, `sessions` (`invalidate_with_sessions`) |
| Create, update or delete a session | `sessions` |
| Create a speaker | `speakers` |
| Update or delete a speaker | `speakers`, `sessions` (schedules embed the speaker name) |
| `close_past_events` script that finishes at least one event | `events`, `sessions` |

Use cases only talk to `EventCache`, `SessionCache` and `SpeakerCache`; no other module
knows a key shape, a namespace or a TTL.

## How it works in Redis

`RedisCache` uses per-namespace versioning:

- An entry lives at `<namespace>:v<version>:<key>`, where the version is read from
  `<namespace>:version` (missing means `0`).
- `invalidate(namespace)` is a single `INCR` of the version key. Older entries become
  unreachable and expire on their own TTL; no key scan or bulk delete is needed.
- Values are JSON strings with `SETEX`.

The `docker-compose.yml` Redis runs with persistence off and
`--maxmemory 64mb --maxmemory-policy allkeys-lru`, which suits a pure cache.

## Payload format

Payloads are the domain objects serialized as JSON with Pydantic `TypeAdapter`
(`EventPage`, `SpeakerPage`, `Speaker`, `list[SessionWithSpeaker]`), not HTTP response
models. The router builds its response from the decoded domain object exactly as it does
on a miss. A stored value that no longer validates (for example after a schema change) is
treated as a miss and rebuilt (`read_through`).

## When Redis is unavailable

- Without `REDIS_URL`, `get_cache` returns `NullCache`: every read is a miss, writes and
  invalidations do nothing. The application is fully functional, just uncached.
- With `REDIS_URL` set and Redis down or slow, `RedisCache` catches Redis and OS errors,
  logs a warning and behaves like `NullCache` for that call. Connect and command timeouts
  are 0.5 s each, so an outage costs at most a short delay per cache call, not an error.
- Errors raised while building the value (for example a not-found) propagate and are never
  cached.

Scripts (`close_past_events`, `seed_demo`) build their own cache the same way: Redis when
`REDIS_URL` is set, `NullCache` otherwise.

## Tests

| Test file | Covers |
| --- | --- |
| `test_cache_policy.py` | Keys, digests, namespaces |
| `test_cached_reads.py` | Read-through and decorators |
| `test_cached_events_api.py`, `test_cached_sessions_api.py`, `test_cached_speakers_api.py` | Endpoint behavior with a `FakeCache` |
| `test_cache_invalidation.py` | Which operations drop which namespaces |
| `test_redis_cache.py` | Versioning and failure handling with fake clients |
| `test_cache_wiring.py`, `test_cache_settings.py` | Adapter selection and TTL settings |

No test needs a running Redis: `FakeCache` and `UnreachableRedis` live in
`backend/tests/fakes.py`.
