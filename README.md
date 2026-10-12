# Mis Eventos

Aplicación de gestión de eventos: los organizadores publican eventos con sesiones y
ponentes, los asistentes se inscriben a los eventos y a las sesiones, y los organizadores
exportan reportes de participantes en CSV. La interfaz está en español.

## Stack

| Parte | Tecnología |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLModel, Alembic (arquitectura hexagonal) |
| Base de datos | PostgreSQL 16 |
| Cache | Redis 7 (opcional) |
| Frontend | React, TypeScript, Vite |
| Pruebas | pytest (backend), Vitest (frontend) |

## Inicio rápido

Requiere Docker con Compose.

```bash
cp backend/.env.example backend/.env    # luego define tu propio JWT_SECRET (32+ caracteres)
docker compose up -d --build
docker compose ps                        # espera a que el backend esté "healthy"
```

Crea el administrador una sola vez, cuando el backend esté saludable (`healthy`). Si se
ejecuta antes falla con `relation "users" does not exist`, porque las migraciones se
aplican al iniciar el backend:

```bash
docker compose exec \
  -e ADMIN_EMAIL=admin@example.com -e ADMIN_PASSWORD='choose-a-password' \
  backend python -m scripts.seed
```

| Servicio | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API del backend | http://localhost:8000/api/v1 |
| Swagger UI | http://localhost:8000/docs |

Datos de demostración opcionales: `docker compose exec -e ADMIN_EMAIL=admin@example.com backend python -m scripts.seed_demo`.

### Frontend sin Docker

Requiere Node.js y el backend en ejecución (`http://localhost:8000/api/v1`):

```bash
cd frontend
npm install
npm run dev     # servidor de desarrollo de Vite en http://localhost:5173
npm test        # pruebas con Vitest
```

Scripts, variables de entorno y cobertura en
[docs/frontend-operations.md](docs/frontend-operations.md).

## Documentación

- [docs/README.md](docs/README.md): índice de todos los documentos.
- [backend/README.md](backend/README.md): configurar, ejecutar y probar el backend.
- [frontend/README.md](frontend/README.md): configurar, ejecutar y probar el frontend.
- [docs/screens.md](docs/screens.md): pantallas de la aplicación.
- [docs/backend-architecture.md](docs/backend-architecture.md): cómo está construido el backend.
- [docs/backend-operations.md](docs/backend-operations.md): configuración, migraciones, carga inicial de datos (seed).
- [docs/backend-testing.md](docs/backend-testing.md): ejecución de pruebas y verificaciones.
- [docs/frontend-architecture.md](docs/frontend-architecture.md): cómo está construido el frontend.
- [docs/frontend-conventions.md](docs/frontend-conventions.md): textos, validaciones, estilos y cómo agregar una pantalla.
- [docs/frontend-operations.md](docs/frontend-operations.md): scripts, Docker, pruebas y cobertura.

Qué leer a continuación: [docs/README.md](docs/README.md) ordena todos los documentos por
pregunta y por tema.

## Estructura del repositorio

```text
backend/    FastAPI service, Alembic migrations, scripts and tests
frontend/   React single-page application
docs/       Documentation
docker-compose.yml
```
