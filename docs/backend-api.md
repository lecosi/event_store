# API del backend

API REST bajo el prefijo `/api/v1`, con JSON de entrada y salida. Los módulos de routers
están en `backend/app/api/v1`; los esquemas de petición y respuesta están en
`backend/app/api`.

## Documentación interactiva

FastAPI sirve el OpenAPI generado en las rutas por defecto:

| Ruta | Qué es |
| --- | --- |
| `/docs` | Swagger UI (usa **Authorize** con un token de `/api/v1/auth/login`) |
| `/redoc` | ReDoc |
| `/openapi.json` | Documento OpenAPI |

Con la configuración de docker compose estas están en `http://localhost:8000/docs` y
similares. Cada operación tiene un resumen (summary), una descripción y respuestas de error
documentadas, por lo que esta página es solo una visión general.

## Autenticación

1. `POST /api/v1/auth/login` con correo y contraseña devuelve `{"access_token": "<jwt>"}`.
2. Envía `Authorization: Bearer <token>` en los endpoints protegidos.

Los tokens son JWT (`HS256` por defecto) y expiran tras `ACCESS_TOKEN_EXPIRE_MINUTES`
(60 por defecto). Los endpoints marcados como "opcional" aceptan un token pero también
funcionan de forma anónima; un token inválido allí se trata como anónimo, nunca como un
error.

## Convenciones

### Errores

Todo cuerpo de error tiene la misma forma:

```json
{ "detail": "Event not found" }
```

| Estado | Significado |
| --- | --- |
| 401 | Token ausente o inválido, o credenciales incorrectas |
| 403 | Autenticado pero sin permiso (rol o propiedad) |
| 404 | Recurso inexistente, o no visible para quien llama (los eventos en borrador parecen inexistentes) |
| 409 | Conflicto con el estado actual: lleno, duplicado, solapamiento, transición inválida |
| 422 | Entrada inválida |

Los errores de dominio se mapean en `app/api/error_handlers.py` (ver
[backend-architecture.md](backend-architecture.md)). Los errores de validación de la forma
de la petición de FastAPI/Pydantic también responden 422, pero entonces `detail` es una
lista de objetos (`loc`, `msg`, `type`) en lugar de una cadena.

### Paginación

Los endpoints de listado reciben `page` (base 1, por defecto 1) y `size` (de 1 a 100, por
defecto 10) y devuelven:

```json
{ "items": [], "total": 25, "page": 1, "size": 10, "pages": 3 }
```

`pages` es `0` cuando no hay resultados. Un `page` o `size` fuera de rango responde 422.

### Fechas y CORS

Las fechas y horas son ISO 8601; los valores sin zona horaria se tratan como UTC. Los
filtros de fecha de los reportes son días UTC simples con formato `YYYY-MM-DD`. Los
orígenes de navegador permitidos provienen de `CORS_ORIGINS`; la cabecera
`Content-Disposition` se expone para que el frontend pueda nombrar las descargas de CSV.

## Endpoints

Leyenda de roles: **público** (sin token), **opcional** (el token cambia el resultado),
**cualquiera** (cualquier usuario autenticado), **organizer** (organizer o admin, más la
propiedad donde se indique), **admin**.

### health

| Método | Ruta | Rol | Propósito |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | público | Verificación de vida (liveness), devuelve `{"status": "ok"}` |

### auth

| Método | Ruta | Rol | Propósito |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | público | Crear una cuenta (siempre `organizer`) |
| POST | `/api/v1/auth/login` | público | Intercambiar credenciales por un token de acceso |
| GET | `/api/v1/users/me` | cualquiera | Perfil del usuario autenticado |

### events

| Método | Ruta | Rol | Propósito |
| --- | --- | --- | --- |
| POST | `/api/v1/events` | organizer | Crear un evento (empieza como `draft`) |
| GET | `/api/v1/events` | opcional | Buscar y paginar eventos (`q`, `status`, `page`, `size`) |
| GET | `/api/v1/events/{event_id}` | opcional | Detalle del evento con sesiones, cantidad de inscritos y disponibilidad |
| PUT | `/api/v1/events/{event_id}` | organizer, propietario | Reemplazar los campos editables |
| PATCH | `/api/v1/events/{event_id}/status` | organizer, propietario | Cambiar el estado siguiendo las transiciones permitidas |
| DELETE | `/api/v1/events/{event_id}` | organizer, propietario | Eliminar el evento y sus dependientes |

"Propietario" es el organizador del evento; los admins pueden gestionar cualquier evento.

### sessions

| Método | Ruta | Rol | Propósito |
| --- | --- | --- | --- |
| GET | `/api/v1/events/{event_id}/sessions` | opcional | Sesiones con ponente, cupos disponibles y la inscripción de quien llama |
| POST | `/api/v1/events/{event_id}/sessions` | organizer, propietario | Programar una sesión |
| PUT | `/api/v1/events/{event_id}/sessions/{session_id}` | organizer, propietario | Reemplazar una sesión |
| DELETE | `/api/v1/events/{event_id}/sessions/{session_id}` | organizer, propietario | Eliminar una sesión (409 si tiene inscripciones) |

### speakers

| Método | Ruta | Rol | Propósito |
| --- | --- | --- | --- |
| POST | `/api/v1/speakers` | organizer | Agregar un ponente al directorio compartido |
| GET | `/api/v1/speakers` | público | Directorio paginado, `q` opcional sobre el nombre |
| GET | `/api/v1/speakers/{speaker_id}` | público | Un ponente |
| PUT | `/api/v1/speakers/{speaker_id}` | organizer | Reemplazar un ponente |
| DELETE | `/api/v1/speakers/{speaker_id}` | organizer | Eliminar (409 si tiene sesiones) |

### registrations

Inscripción a un evento e inscripción a una sesión. Todos requieren un token (cualquier rol).

| Método | Ruta | Propósito |
| --- | --- | --- |
| POST | `/api/v1/events/{event_id}/register` | Inscribirse a un evento |
| DELETE | `/api/v1/events/{event_id}/register` | Cancelar la inscripción (también cancela sus inscripciones a sesiones) |
| GET | `/api/v1/users/me/events` | Eventos paginados a los que está inscrito quien llama |
| POST | `/api/v1/events/{event_id}/sessions/{session_id}/register` | Inscribirse a una sesión |
| DELETE | `/api/v1/events/{event_id}/sessions/{session_id}/register` | Cancelar la inscripción a la sesión |

### reports

Rol: organizer o admin. Los organizadores solo ven sus propios eventos. Filtros: `event_id`,
`q`, `status`, `date_from`, `date_to` (y `session_id` para los reportes de sesiones).

| Método | Ruta | Propósito |
| --- | --- | --- |
| GET | `/api/v1/reports/participants` | Vista previa paginada de las personas inscritas |
| GET | `/api/v1/reports/participants.csv` | Mismos filtros, todo el resultado como descarga CSV |
| GET | `/api/v1/reports/sessions/participants` | Vista previa paginada de las personas inscritas a sesiones |
| GET | `/api/v1/reports/sessions/participants.csv` | Mismos filtros, todo el resultado como descarga CSV |

El formato del CSV y los nombres de archivo se describen en
[backend-domain-rules.md](backend-domain-rules.md#reportes-y-csv).

### admin

Rol: admin.

| Método | Ruta | Propósito |
| --- | --- | --- |
| GET | `/api/v1/admin/users` | Usuarios paginados, búsqueda opcional por prefijo de `email` |
| PATCH | `/api/v1/admin/users/{user_id}` | Actualización parcial de nombre, correo, rol o indicador de activo |

## Mantener esta página al día

Las tablas de arriba se verificaron contra el OpenAPI generado. Para volver a listar los
endpoints reales:

```bash
cd backend   # JWT_SECRET must be set, see backend-operations.md
poetry run python -c "from app.main import app; \
[print(m.upper(), p) for p, ms in app.openapi()['paths'].items() for m in ms]"
```

`backend/tests/test_router_structure.py` y los archivos `test_*_api.py` documentan mediante
pruebas el comportamiento de cada endpoint.
