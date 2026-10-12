# Backend de Mis Eventos

API REST de **Mis Eventos**: eventos con sesiones y ponentes, inscripciones y reportes
CSV de participantes. Está construida con Python 3.12, FastAPI, SQLModel y Alembic, sobre
PostgreSQL 16, con Redis 7 como cache opcional. Sigue una arquitectura hexagonal.

## Mapa de `app/`

| Carpeta | Responsabilidad |
| --- | --- |
| `domain/` | Reglas de negocio puras: eventos, sesiones, inscripciones, roles |
| `application/` | Casos de uso (servicios) y puertos que definen lo que necesitan |
| `infrastructure/` | Adaptadores: base de datos (`db/`), cache (`cache/`), seguridad (`security/`) |
| `api/` | Rutas HTTP (`v1/`), esquemas, manejo de errores y metadatos OpenAPI |
| `core/` | Configuración leída del entorno (`config.py`) |

## Configurar

```bash
cp .env.example .env     # desde backend/
```

El archivo de ejemplo trae `JWT_SECRET=change-me` y la aplicación se niega a iniciar con
ese valor: reemplázalo por uno propio de 32+ caracteres.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `JWT_SECRET` | ninguno (obligatorio) | Clave de firma de los tokens |
| `DATABASE_URL` | PostgreSQL local `mis_eventos` | URL de la base de datos |
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes de navegador permitidos, separados por comas |
| `REDIS_URL` | sin definir | Activa el cache; sin valor no hay cache |

Lista completa en [../docs/backend-operations.md](../docs/backend-operations.md).

## Ejecutar

Con Docker Compose, desde la raíz del repositorio (aplica las migraciones al iniciar):

```bash
docker compose up -d --build
docker compose ps                         # espera a que el backend esté "healthy"
curl http://localhost:8000/api/v1/health  # {"status":"ok"}
```

Sin Docker para el backend, con PostgreSQL disponible:

```bash
docker compose up -d db                   # desde la raíz, o cualquier PostgreSQL 16
cd backend
poetry install
poetry run alembic upgrade head           # migraciones
poetry run uvicorn app.main:app --reload  # http://localhost:8000
```

Crear el administrador y los datos de demostración: ver la sección de seed en
[../docs/backend-operations.md](../docs/backend-operations.md).

## Probar

Las pruebas de integración necesitan PostgreSQL. Con la base de datos de Compose hay que
indicar sus credenciales (`mis_eventos:mis_eventos`); el nombre de la base debe terminar
en `_test` y se crea automáticamente.

```bash
docker compose up -d db                   # desde la raíz
cd backend
export TEST_DATABASE_URL=postgresql+psycopg://mis_eventos:mis_eventos@localhost:5432/mis_eventos_test
poetry run pytest                         # todas
poetry run pytest -m unit                 # sin base de datos
poetry run pytest --cov=app --cov-report=term-missing   # cobertura (mínimo 90 %)
poetry run ruff check app scripts tests   # lint
poetry run mypy                           # tipos
```

Detalles en [../docs/backend-testing.md](../docs/backend-testing.md) y
[../docs/coverage/README.md](../docs/coverage/README.md).

## Documentación de la API

Con el backend en ejecución, Swagger UI está en http://localhost:8000/docs. El resumen de
endpoints, autenticación y formato de errores está en
[../docs/backend-api.md](../docs/backend-api.md).

## Más documentación

- [../docs/backend-architecture.md](../docs/backend-architecture.md): capas, puertos y adaptadores.
- [../docs/backend-domain-rules.md](../docs/backend-domain-rules.md): reglas de negocio.
- [../docs/backend-cache.md](../docs/backend-cache.md): qué se cachea y cómo se invalida.
- [../docs/backend-scripts.md](../docs/backend-scripts.md): `seed`, `seed_demo` y `close_past_events`.
