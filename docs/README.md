# Documentation

Index of the project documentation, in suggested reading order. The backend documents
describe the code as it is today and reference the real files.

## Start here

| Document | What it covers |
| --- | --- |
| [../README.md](../README.md) | What the project is and how to run it in a few commands |
| [screens.md](screens.md) | Application screens, with reserved spaces for screenshots |

## Backend: understand it

| Document | What it covers |
| --- | --- |
| [backend-architecture.md](backend-architecture.md) | Hexagonal layers, ports and adapters, unit of work, composition root, error mapping, one request end to end, SOLID examples |
| [backend-domain-rules.md](backend-domain-rules.md) | Business rules: roles, event lifecycle, registrations, session enrollments, speakers, reports and CSV, user administration |
| [backend-api.md](backend-api.md) | Endpoint overview by tag, authentication, error format, pagination |
| [backend-cache.md](backend-cache.md) | What is cached, keys, TTLs, invalidation, behavior without Redis |

## Backend: work with it

| Document | What it covers |
| --- | --- |
| [backend-testing.md](backend-testing.md) | Running tests, fakes versus PostgreSQL, coverage, lint and type checks |
| [backend-operations.md](backend-operations.md) | Docker Compose, environment variables, migrations, seeding |
| [backend-scripts.md](backend-scripts.md) | `seed`, `seed_demo` and `close_past_events` scripts, scheduling |
| [coverage/README.md](coverage/README.md) | Test coverage summaries and how to regenerate the reports |

## Which document for which question

- "How is it built and why?" -> architecture, then domain rules.
- "What can this endpoint do and who may call it?" -> API, then domain rules.
- "How do I run or deploy it?" -> operations, then scripts.
- "How do I add a feature safely?" -> architecture (layers and ports), testing.
