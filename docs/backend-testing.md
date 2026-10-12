# Backend testing

The backend suite is pytest, in `backend/tests`. Static checks are Ruff and mypy.
All commands run from `backend/` with Poetry (`poetry install` once).

## Quick start

```bash
# from the repository root: PostgreSQL for the integration tests
docker compose up -d db          # set DB_HOST_PORT if 5432 is busy

cd backend
poetry run pytest                # everything
poetry run pytest -m unit        # no database needed
poetry run pytest -m integration # needs PostgreSQL
poetry run pytest tests/test_session_registration_service.py -k overlap
```

Redis is not needed: the cache is tested through fakes (see
[backend-cache.md](backend-cache.md)).

## Test database

`backend/tests/conftest.py` resolves the database in this order:

1. `TEST_DATABASE_URL`, when set.
2. `DATABASE_URL` (from the environment or `backend/.env`) with `_test` appended to the
   database name, for example `mis_eventos_test`.

The database name must end in `_test`; otherwise the run aborts, so a real database is
never truncated. The suite then:

- creates the database when it is missing (connecting through the `postgres` database);
- runs `alembic upgrade head` once per session, so migrations are exercised too;
- truncates every table (`RESTART IDENTITY CASCADE`) before and after each test that uses
  the database.

If PostgreSQL is unreachable the run exits with a message telling you to start it or set
`TEST_DATABASE_URL`.

## Layout

| Kind | Files | Runs against |
| --- | --- | --- |
| Domain rules | `test_event_domain.py`, `test_session_domain.py`, `test_session_registration_domain.py` | Nothing (pure functions) |
| Use cases (services) | `test_*_service.py`, `test_session_catalogue.py`, `test_close_past_events.py`, `test_report_service.py` | In-memory fakes |
| HTTP API | `test_*_api.py` | FastAPI `TestClient` and PostgreSQL |
| SQL adapters | `test_*_repository.py`, `test_unit_of_work.py`, `test_models.py`, `test_migration_full_name.py` | PostgreSQL |
| Concurrency | `test_registration_concurrency_postgres.py`, `test_session_registration_concurrency_postgres.py` | PostgreSQL, threads |
| Cache | `test_cache_*.py`, `test_cached_*.py`, `test_redis_cache.py` | Fakes (`FakeCache`, `UnreachableRedis`) |
| Wiring and structure | `test_router_structure.py`, `test_error_handlers.py`, `test_config.py`, `test_cors.py`, `test_security.py` | Mostly nothing |
| Scripts | `test_seed.py`, `test_seed_demo.py`, `test_close_past_events_script.py` | Fakes or PostgreSQL |

### Markers

`pytest.mark.unit` and `pytest.mark.integration` are applied automatically by
`pytest_collection_modifyitems` in `conftest.py`: a test is `integration` when it uses one
of the fixtures `postgres_engine`, `clean_postgres`, `session` or `client`, `unit`
otherwise. Nothing needs to be marked by hand, and `--strict-markers` is on.

### Fakes versus PostgreSQL

- Service tests use the in-memory implementations in `backend/tests/fakes.py`
  (`FakeUnitOfWork`, `FakeUserRepository`, `FakeEventRepository`, ...). They are fast and
  assert business rules, including that a failing use case rolls back and does not
  invalidate the cache. Time is injected through a clock argument.
- API and repository tests use real PostgreSQL, because behavior such as `FOR UPDATE`
  locks, `CHECK` constraints, `ON DELETE CASCADE`, `ILIKE` escaping and index-backed prefix
  search cannot be trusted in a fake.
- The `*_concurrency_postgres.py` tests fire many parallel requests through a
  `ThreadPoolExecutor` against the same event or session and assert that capacity is never
  exceeded and duplicates are rejected. The engine pool is sized (`POOL_SIZE = 12`) for this.

### Useful fixtures (`conftest.py`)

| Fixture | Provides |
| --- | --- |
| `client` | `TestClient` over a fresh app, with the DB session overridden |
| `session` | A SQLModel `Session` on the clean test database |
| `fake_cache` | Replaces the cache dependency with `FakeCache` |
| `unreachable_cache` | A `RedisCache` whose client always fails |
| `override_settings` | Overrides fields of `Settings` for the app under test |

`JWT_SECRET` is defaulted to a test-only value in `conftest.py`, so tests do not depend on
your `.env` secret.

## Coverage

```bash
cd backend
poetry run pytest --cov=app --cov-report=term-missing           # terminal
poetry run pytest --cov=app --cov-report=term-missing --cov-report=html   # htmlcov/index.html
```

Configuration is in `backend/pyproject.toml`: line and branch coverage over `app`,
`fail_under = 90` (the run fails below 90 percent), fully covered files are hidden from the
report. The latest recorded summary is `docs/coverage/backend.txt`; how to regenerate the
reports is in [coverage/README.md](coverage/README.md). `htmlcov/`, `coverage.xml` and
`.coverage` are gitignored.

## Lint and type checks

```bash
cd backend
poetry run ruff check app scripts tests
poetry run ruff format --check app scripts tests
poetry run mypy                      # files = app, scripts (see pyproject.toml)
```

- Ruff: line length 100, rule sets `E`, `F`, `I`, `UP`, `B`.
- mypy: `disallow_untyped_defs`, `check_untyped_defs`, `warn_return_any` and related
  strictness flags; tests are not type-checked.
- Running `ruff check .` without paths also scans `alembic/versions`, where the initial
  migrations currently report a few import-style findings that predate these docs.

## Writing a test

1. Domain rule: call the pure function with plain dataclasses; no fixtures.
2. Use case: build the service with the fakes from `tests/fakes.py` and an injected clock.
3. Endpoint: use `client` and the helpers already present in the nearest `test_*_api.py`.
4. Name the behavior in the test name; keep intent out of comments.
