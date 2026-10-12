# Cobertura de pruebas

Resúmenes en texto de las últimas ejecuciones de cobertura. Los reportes HTML completos
son artefactos de compilación, están ignorados por git y se regeneran localmente con los
comandos de abajo.

| Archivo | Suite | Comando |
| --- | --- | --- |
| [`backend.txt`](backend.txt) | pytest + pytest-cov (líneas y ramas) | `poetry run pytest --cov=app --cov-report=term-missing` |
| [`frontend.txt`](frontend.txt) | Vitest + v8 | `npm run test:coverage` |

## Regenerar los reportes HTML

### Backend (`backend/htmlcov/index.html`)

Las pruebas de integración necesitan una instancia de PostgreSQL. El nombre de la base de
datos de pruebas debe terminar en `_test`; se crea automáticamente si no existe.

```bash
# desde la raíz del repositorio
docker compose up -d db redis        # define DB_HOST_PORT si el 5432 está ocupado
cd backend
poetry install
poetry run pytest --cov=app --cov-report=term-missing --cov-report=html
# abre htmlcov/index.html
```

Si la base de datos no usa la configuración por defecto, apunta la suite a ella con
`DATABASE_URL` (se le agrega el sufijo `_test`) o con `TEST_DATABASE_URL`.

Con la base de datos de `docker compose` hay que indicar sus credenciales (usuario y
contraseña `mis_eventos`, definidas en `docker-compose.yml`); sin eso la suite intenta
conectarse con el usuario del sistema operativo y falla por autenticación:

```bash
cd backend
TEST_DATABASE_URL=postgresql+psycopg://mis_eventos:mis_eventos@localhost:5432/mis_eventos_test \
  poetry run pytest --cov=app --cov-report=term-missing
```

### Frontend (`frontend/coverage/index.html`)

```bash
cd frontend
npm install
npm run test:coverage
# abre coverage/index.html
```

La suite del frontend no necesita servicios externos.

`htmlcov/`, `coverage/` y `coverage.xml` están ignorados por git; solo los resúmenes en
texto de este directorio se versionan.
