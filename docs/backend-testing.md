# Pruebas del backend

La suite del backend es pytest, en `backend/tests`. Las verificaciones estáticas son Ruff y
mypy. Todos los comandos se ejecutan desde `backend/` con Poetry (`poetry install` una vez).

## Inicio rápido

```bash
# from the repository root: PostgreSQL for the integration tests
docker compose up -d db          # set DB_HOST_PORT if 5432 is busy

cd backend
poetry run pytest                # everything
poetry run pytest -m unit        # no database needed
poetry run pytest -m integration # needs PostgreSQL
poetry run pytest tests/test_session_registration_service.py -k overlap
```

Redis no es necesario: el cache se prueba mediante fakes (ver
[backend-cache.md](backend-cache.md)).

## Base de datos de pruebas

`backend/tests/conftest.py` resuelve la base de datos en este orden:

1. `TEST_DATABASE_URL`, cuando está definida.
2. `DATABASE_URL` (del entorno o de `backend/.env`) con `_test` agregado al nombre de la
   base de datos, por ejemplo `mis_eventos_test`.

El nombre de la base de datos debe terminar en `_test`; de lo contrario la ejecución se
aborta, de modo que nunca se trunca una base de datos real. Luego la suite:

- crea la base de datos cuando no existe (conectándose a través de la base `postgres`);
- ejecuta `alembic upgrade head` una vez por sesión, de modo que las migraciones también se
  ejercitan;
- trunca todas las tablas (`RESTART IDENTITY CASCADE`) antes y después de cada prueba que
  usa la base de datos.

Si PostgreSQL no es alcanzable, la ejecución termina con un mensaje que indica iniciarlo o
definir `TEST_DATABASE_URL`.

## Organización

| Tipo | Archivos | Se ejecuta contra |
| --- | --- | --- |
| Reglas de dominio | `test_event_domain.py`, `test_session_domain.py`, `test_session_registration_domain.py` | Nada (funciones puras) |
| Casos de uso (servicios) | `test_*_service.py`, `test_session_catalogue.py`, `test_close_past_events.py`, `test_report_service.py` | Fakes en memoria |
| API HTTP | `test_*_api.py` | `TestClient` de FastAPI y PostgreSQL |
| Adaptadores SQL | `test_*_repository.py`, `test_unit_of_work.py`, `test_models.py`, `test_migration_full_name.py` | PostgreSQL |
| Concurrencia | `test_registration_concurrency_postgres.py`, `test_session_registration_concurrency_postgres.py` | PostgreSQL, hilos |
| Cache | `test_cache_*.py`, `test_cached_*.py`, `test_redis_cache.py` | Fakes (`FakeCache`, `UnreachableRedis`) |
| Cableado y estructura | `test_router_structure.py`, `test_error_handlers.py`, `test_config.py`, `test_cors.py`, `test_security.py` | Casi nada |
| Scripts | `test_seed.py`, `test_seed_demo.py`, `test_close_past_events_script.py` | Fakes o PostgreSQL |

### Markers

`pytest.mark.unit` y `pytest.mark.integration` se aplican automáticamente mediante
`pytest_collection_modifyitems` en `conftest.py`: una prueba es `integration` cuando usa
alguno de los fixtures `postgres_engine`, `clean_postgres`, `session` o `client`, y `unit`
en caso contrario. No hace falta marcar nada a mano, y `--strict-markers` está activo.

### Fakes frente a PostgreSQL

- Las pruebas de servicios usan las implementaciones en memoria de
  `backend/tests/fakes.py` (`FakeUnitOfWork`, `FakeUserRepository`,
  `FakeEventRepository`, ...). Son rápidas y verifican reglas de negocio, incluido que un
  caso de uso que falla hace rollback y no invalida el cache. El tiempo se inyecta mediante
  un argumento de reloj (clock).
- Las pruebas de API y de repositorios usan PostgreSQL real, porque comportamientos como
  los bloqueos `FOR UPDATE`, las restricciones `CHECK`, `ON DELETE CASCADE`, el escapado de
  `ILIKE` y la búsqueda por prefijo respaldada por índice no se puede confiar en un fake.
- Las pruebas `*_concurrency_postgres.py` lanzan muchas peticiones paralelas mediante un
  `ThreadPoolExecutor` contra el mismo evento o sesión y verifican que nunca se excede la
  capacidad y que los duplicados se rechazan. El pool del motor está dimensionado
  (`POOL_SIZE = 12`) para esto.

### Fixtures útiles (`conftest.py`)

| Fixture | Provee |
| --- | --- |
| `client` | `TestClient` sobre una app nueva, con la sesión de BD sobrescrita |
| `session` | Una `Session` de SQLModel sobre la base de datos de pruebas limpia |
| `fake_cache` | Reemplaza la dependencia de cache por `FakeCache` |
| `unreachable_cache` | Un `RedisCache` cuyo cliente siempre falla |
| `override_settings` | Sobrescribe campos de `Settings` para la app bajo prueba |

`JWT_SECRET` toma por defecto un valor solo para pruebas en `conftest.py`, de modo que las
pruebas no dependen del secreto de tu `.env`.

## Cobertura

```bash
cd backend
poetry run pytest --cov=app --cov-report=term-missing           # terminal
poetry run pytest --cov=app --cov-report=term-missing --cov-report=html   # htmlcov/index.html
```

La configuración está en `backend/pyproject.toml`: cobertura de líneas y de ramas sobre
`app`, `fail_under = 90` (la ejecución falla por debajo del 90 por ciento), y los archivos
totalmente cubiertos se ocultan del reporte. El último resumen registrado es
`docs/coverage/backend.txt`; cómo regenerar los reportes está en
[coverage/README.md](coverage/README.md). `htmlcov/`, `coverage.xml` y `.coverage` están en
gitignore.

## Lint y verificación de tipos

```bash
cd backend
poetry run ruff check app scripts tests
poetry run ruff format --check app scripts tests
poetry run mypy                      # files = app, scripts (see pyproject.toml)
```

- Ruff: longitud de línea 100, conjuntos de reglas `E`, `F`, `I`, `UP`, `B`.
- mypy: `disallow_untyped_defs`, `check_untyped_defs`, `warn_return_any` y otras opciones
  de rigurosidad relacionadas; las pruebas no se verifican por tipos.
- Ejecutar `ruff check .` sin rutas también analiza `alembic/versions`, donde las
  migraciones iniciales reportan actualmente algunos hallazgos de estilo de imports que son
  anteriores a esta documentación.

## Escribir una prueba

1. Regla de dominio: llama a la función pura con dataclasses simples; sin fixtures.
2. Caso de uso: construye el servicio con los fakes de `tests/fakes.py` y un reloj
   inyectado.
3. Endpoint: usa `client` y los helpers que ya existen en el `test_*_api.py` más cercano.
4. Nombra el comportamiento en el nombre de la prueba; deja la intención fuera de los
   comentarios.
