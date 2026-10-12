# Mis Eventos

Event management application: organizers publish events with sessions and speakers,
attendees register to events and enroll in sessions, and organizers export participant
reports as CSV. The interface is in Spanish.

## Stack

| Part | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLModel, Alembic (hexagonal architecture) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (optional) |
| Frontend | React, TypeScript, Vite |
| Tests | pytest (backend), Vitest (frontend) |

## Quick start

Requires Docker with Compose.

```bash
cp backend/.env.example backend/.env    # then set your own JWT_SECRET (32+ characters)
docker compose up -d --build
docker compose ps                        # wait until backend is "healthy"
```

Create the administrator once the backend is healthy (running it earlier fails with
`relation "users" does not exist`, because migrations run at backend start):

```bash
docker compose exec \
  -e ADMIN_EMAIL=admin@example.com -e ADMIN_PASSWORD='choose-a-password' \
  backend python -m scripts.seed
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/v1 |
| Swagger UI | http://localhost:8000/docs |

Optional demo data: `docker compose exec -e ADMIN_EMAIL=admin@example.com backend python -m scripts.seed_demo`.

## Documentation

- [docs/README.md](docs/README.md): index of all documents.
- [docs/screens.md](docs/screens.md): application screens.
- [docs/backend-architecture.md](docs/backend-architecture.md): how the backend is built.
- [docs/backend-operations.md](docs/backend-operations.md): configuration, migrations, seeding.
- [docs/backend-testing.md](docs/backend-testing.md): running tests and checks.

## Repository layout

```text
backend/    FastAPI service, Alembic migrations, scripts and tests
frontend/   React single-page application
docs/       Documentation
docker-compose.yml
```
