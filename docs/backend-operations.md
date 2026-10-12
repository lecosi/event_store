# Operación del backend

Cómo ejecutar, configurar y mantener el backend. Para los scripts en detalle ver
[backend-scripts.md](backend-scripts.md).

## Ejecutar con Docker Compose

`docker-compose.yml` define cuatro servicios:

| Servicio | Imagen / build | Puerto del host | Notas |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | `127.0.0.1:${DB_HOST_PORT:-5432}` | Volumen `db_data`; healthcheck con `pg_isready` |
| `redis` | `redis:7-alpine` | ninguno | Solo cache: sin persistencia, 64 MB, `volatile-lru` |
| `backend` | `./backend` | `8000` | Inicia después de que `db` y `redis` estén saludables (healthy) |
| `frontend` | `./frontend` | `5173` (puerto del contenedor 80) | Build estático, llama al backend desde el navegador |

```bash
cp backend/.env.example backend/.env     # solo la primera vez; compose lee este archivo
docker compose up -d --build
docker compose ps                         # espera a que el backend esté "healthy"
curl http://localhost:8000/api/v1/health  # {"status":"ok"}
```

Luego abre `http://localhost:5173` (aplicación) o `http://localhost:8000/docs` (Swagger UI).

Reemplaza el `JWT_SECRET` del archivo de ejemplo por un valor propio; genera uno con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Detén con `docker compose down` (agrega `-v` para eliminar el volumen de la base de datos).

### Qué hace el contenedor del backend

`backend/Dockerfile` construye una imagen multi-stage que corre como usuario sin privilegios
de root. `backend/docker-entrypoint.sh` ejecuta, en orden:

1. `alembic upgrade head` (aplica las migraciones pendientes);
2. `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

El healthcheck de su imagen llama a `GET /api/v1/health` (período de inicio de 20 s). Como
las migraciones se ejecutan antes de que arranque el servidor, el contenedor solo se
vuelve saludable una vez que existe el esquema.

## Configuración

Los ajustes provienen de variables de entorno, con `backend/.env` como respaldo cuando se
ejecuta fuera de Docker (`backend/app/core/config.py`). Con Compose, `backend/.env` se pasa
como `env_file`, y Compose sobrescribe `DATABASE_URL`, `REDIS_URL` y `CORS_ORIGINS` para el
servicio `backend`.

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL local `mis_eventos` (`postgresql+psycopg://...`) | URL de SQLAlchemy de la base de datos |
| `JWT_SECRET` | ninguno (obligatorio) | Clave de firma; al menos 32 caracteres y distinta de `change-me`, o la aplicación se niega a iniciar |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma del JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Duración del token |
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes de navegador permitidos, separados por comas |
| `REDIS_URL` | sin definir | Habilita el cache Redis; sin definir significa sin cache (`NullCache`) |
| `CACHE_TTL_EVENTS_SECONDS` | `60` | TTL de los listados de eventos cacheados (debe ser > 0) |
| `CACHE_TTL_SESSIONS_SECONDS` | `120` | TTL de los horarios de eventos cacheados (debe ser > 0) |
| `CACHE_TTL_SPEAKERS_SECONDS` | `300` | TTL de las lecturas de ponentes cacheadas (debe ser > 0) |
| `APP_NAME` | `Mis Eventos` | Título mostrado en el documento OpenAPI |
| `ADMIN_FULL_NAME` | `Administrator` | Nombre completo asignado al admin creado por el seed |

Leídas solo por los scripts, sin valor por defecto:

| Variable | Usada por | Significado |
| --- | --- | --- |
| `ADMIN_EMAIL` | `scripts.seed`, `scripts.seed_demo` | Correo del administrador |
| `ADMIN_PASSWORD` | `scripts.seed` | Contraseña del administrador (al menos 8 caracteres) |

Variables a nivel de Compose (shell o un archivo `.env` en la raíz): `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB` (todas con valor por defecto `mis_eventos`),
`DB_HOST_PORT` (por defecto `5432`), `CORS_ORIGINS` y `VITE_API_URL` (argumento de build del
frontend, por defecto `http://localhost:8000/api/v1`).

`backend/.env.example` no incluye `ADMIN_EMAIL` ni `ADMIN_PASSWORD`; agrégalas a
`backend/.env` o pásalas con `-e` como se muestra más abajo.

## Migraciones

Alembic vive en `backend/alembic` (configuración en `backend/alembic.ini`). La URL proviene
de `DATABASE_URL`.

```bash
cd backend
poetry run alembic upgrade head                              # aplicar
poetry run alembic current                                   # en qué revisión está la base de datos
poetry run alembic revision --autogenerate -m "describe it"  # nueva migración
```

Dentro de Docker el entrypoint aplica las migraciones en cada inicio, por lo que un
despliegue normal no necesita ningún paso manual. Las revisiones existentes están en
`backend/alembic/versions` (`0001` a `0006`). Revisa a mano las migraciones autogeneradas y
agrega una prueba cuando una cambie datos (`backend/tests/test_migration_full_name.py` es un
ejemplo).

## Carga inicial de datos (seed)

Ejecuta los seeds solo después de que el contenedor del backend reporte estado saludable:
las migraciones crean las tablas, y ejecutar un seed antes de que terminen falla con
`relation "users" does not exist`.

```bash
# administrador (lo crea, o promueve una cuenta existente a admin)
docker compose exec \
  -e ADMIN_EMAIL=admin@example.com -e ADMIN_PASSWORD='choose-a-password' \
  backend python -m scripts.seed

# datos de demostración opcionales (ponentes, eventos, sesiones, inscripciones, asistentes)
docker compose exec -e ADMIN_EMAIL=admin@example.com \
  backend python -m scripts.seed_demo
```

- `scripts.seed` es idempotente: crea el admin o promueve la cuenta existente, conservando
  su propio nombre completo.
- `scripts.seed_demo` requiere que ese admin exista y no hace nada cuando ya existen
  eventos. También crea cinco cuentas de asistentes e imprime sus credenciales; esas
  cuentas son solo para demostración. Registra una cuenta nueva en la aplicación para
  obtener un organizer.

Fuera de Docker, ejecuta los mismos módulos desde `backend/` con
`poetry run python -m scripts.<name>` y las variables exportadas.

## Mantenimiento programado

`python -m scripts.close_past_events` mueve a `finished` los eventos publicados que ya
terminaron. Nada lo ejecuta automáticamente; prográmalo (ejemplo de cron en
[backend-scripts.md](backend-scripts.md)).

## Ejecución sin Docker

```bash
docker compose up -d db redis        # o cualquier PostgreSQL 16 / Redis
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Define `REDIS_URL=redis://localhost:6379/0` en `backend/.env` para usar el cache. Ten en
cuenta que el servicio `redis` de compose no publica un puerto del host, por lo que para
ejecuciones en el host usa tu propio Redis o deja `REDIS_URL` sin definir.

## Solución de problemas

| Síntoma | Causa | Solución |
| --- | --- | --- |
| El backend termina al iniciar con un mensaje sobre `JWT_SECRET` | Secreto ausente, corto o de ejemplo | Define un valor aleatorio de 32+ caracteres |
| `compose up` falla porque falta el archivo de entorno | Falta `backend/.env` | `cp backend/.env.example backend/.env` |
| El seed falla con `relation "users" does not exist` | Las migraciones aún no terminaron | Espera a que `docker compose ps` muestre `healthy` y reintenta |
| El seed imprime `ADMIN_EMAIL and ADMIN_PASSWORD must be set` | Las variables no están en el contenedor | Pásalas con `-e` o agrégalas a `backend/.env` y recrea el contenedor |
| El navegador muestra errores de CORS | El origen del frontend no está en `CORS_ORIGINS` | Agrégalo (separado por comas) y reinicia el backend |
| El puerto 5432 ya está en uso | PostgreSQL local | Define `DB_HOST_PORT` con otro puerto |
