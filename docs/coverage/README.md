# Test coverage

Text summaries of the latest coverage runs. The full HTML reports are build
artifacts and are gitignored; regenerate them locally with the commands below.

| File | Suite | Command |
| --- | --- | --- |
| [`backend.txt`](backend.txt) | pytest + pytest-cov (line and branch) | `poetry run pytest --cov=app --cov-report=term-missing` |
| [`frontend.txt`](frontend.txt) | Vitest + v8 | `npm run test:coverage` |

## Regenerate the HTML reports

### Backend (`backend/htmlcov/index.html`)

The integration tests need a PostgreSQL instance. The test database name must
end in `_test`; it is created automatically if missing.

```bash
# from the repository root
docker compose up -d db redis        # set DB_HOST_PORT if 5432 is busy
cd backend
poetry install
poetry run pytest --cov=app --cov-report=term-missing --cov-report=html
# open htmlcov/index.html
```

If the database is not on the default settings, point the suite at it with
`DATABASE_URL` (the `_test` suffix is appended) or `TEST_DATABASE_URL`.

### Frontend (`frontend/coverage/index.html`)

```bash
cd frontend
npm install
npm run test:coverage
# open coverage/index.html
```

No external services are required for the frontend suite.

`htmlcov/`, `coverage/` and `coverage.xml` are gitignored; only the text
summaries in this directory are versioned.
