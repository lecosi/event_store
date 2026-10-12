# Cache del backend

En el proyecto existen endpoints de lectura públicos, los cuales tienen uso constante y por definición no es necesario tener en tiempo real la información que entregan. Por ello, se implementa un sistema de cache con `Redis`.

Mapa del código:

| Aspecto | Archivo |
| --- | --- |
| Puerto `Cache`, nombres de namespace | `backend/app/application/ports.py` |
| Claves, TTL e invalidación por agregado | `backend/app/application/cache_policy.py` |
| Decoradores con cache de los casos de uso de lectura | `backend/app/infrastructure/cache/cached_readers.py` |
| Helper de read-through | `backend/app/infrastructure/cache/read_through.py` |
| Adaptador Redis | `backend/app/infrastructure/cache/redis_cache.py` |
| Adaptador sin efecto (no-op) | `backend/app/infrastructure/cache/null_cache.py` |
| Conexión | `get_cache`, `get_*_cache` en `backend/app/api/dependencies.py` |

## Qué se cachea

| Namespace | Lectura cacheada | Clave (dentro del namespace) | Variable de TTL (por defecto) |
| --- | --- | --- | --- |
| `events` | Páginas del listado público de eventos | `list:<sha256(q)\|->:<status\|any>:<page>:<size>` | `CACHE_TTL_EVENTS_SECONDS` (60) |
| `sessions` | Horario de un evento (sesiones con nombre del ponente) | `event:<event_id>` | `CACHE_TTL_SESSIONS_SECONDS` (120) |
| `speakers` | Página del directorio | `list:<sha256(q)\|->:<page>:<size>` | `CACHE_TTL_SPEAKERS_SECONDS` (300) |
| `speakers` | Un ponente | `detail:<speaker_id>` | `CACHE_TTL_SPEAKERS_SECONDS` (300) |

### Qué no se cachea

- El listado de eventos para organizadores y administradores: ven eventos no publicados,
  por lo que solo los usuarios anónimos y los asistentes (`is_public_view`) comparten la
  vista pública cacheada.
- El detalle del evento (`GET /events/{id}`), "mis eventos" y los reportes.
- La disponibilidad de sesiones por usuario (`enrolled_count`, `available_spots`,
  `is_enrolled`): `SessionCatalogue` combina el horario cacheado con conteos en vivo en cada
  petición, por lo que inscribirse nunca requiere invalidar nada.

## Invalidación

La invalidación es explícita y siempre se ejecuta después de confirmar la transacción, de
modo que una reversión deja el cache intacto.

| Operación | Namespaces descartados |
| --- | --- |
| Crear, actualizar o cambiar el estado de un evento | `events` |
| Eliminar un evento | `events`, `sessions` (`invalidate_with_sessions`) |
| Crear, actualizar o eliminar una sesión | `sessions` |
| Crear un ponente | `speakers` |
| Actualizar o eliminar un ponente | `speakers`, `sessions` (los horarios incluyen el nombre del ponente) |
| Script `close_past_events` que finaliza al menos un evento | `events`, `sessions` |

Los casos de uso solo hablan con `EventCache`, `SessionCache` y `SpeakerCache`; ningún otro
módulo conoce la forma de una clave, un namespace ni un TTL.

## Cómo funciona en Redis

`RedisCache` usa versionado por namespace:

- Una entrada vive en `<namespace>:v<version>:<key>`, donde la versión se lee de
  `<namespace>:version` (si falta, es `0`).
- `invalidate(namespace)` es un único `INCR` de la clave de versión. Las entradas antiguas
  quedan inalcanzables y expiran por su propio TTL; no hace falta recorrer claves ni
  borrar en bloque.

El Redis de `docker-compose.yml` corre sin persistencia y con
`--maxmemory 64mb --maxmemory-policy volatile-lru`.

La política `volatile-lru` es intencional. Las entradas se escriben con TTL, pero las
claves `<namespace>:version` no tienen ninguno. Con `volatile-lru` solo las claves que
tienen TTL son candidatas a ser desalojadas, por lo que una clave de versión nunca puede
ser desalojada por desborde de memoria. Con `allkeys-lru`, una clave de versión desalojada
volvería a `0`, y las entradas escritas antes bajo una versión reutilizada (por ejemplo
`speakers:v1:list`) podrían volver a ser alcanzables y servir datos obsoletos hasta que
expire su TTL (300 s como máximo). El resto del cache se comporta como antes: cuando la
memoria está llena, se descartan primero las entradas menos recientemente usadas.

## Formato del payload

Los payloads son los objetos de dominio serializados como JSON con `TypeAdapter` de
Pydantic (`EventPage`, `SpeakerPage`, `Speaker`, `list[SessionWithSpeaker]`), no modelos de
respuesta HTTP. El router construye su respuesta a partir del objeto de dominio
decodificado exactamente igual que ante un fallo de cache (miss). Un valor almacenado que
ya no valida (por ejemplo tras un cambio de esquema) se trata como un miss y se reconstruye
(`read_through`).

## Cuando Redis no está disponible

- Sin `REDIS_URL`, `get_cache` devuelve `NullCache`: toda lectura es un miss, y las
  escrituras e invalidaciones no hacen nada. La aplicación es totalmente funcional, solo
  que sin cache.
- Con `REDIS_URL` definida y Redis caído o lento, `RedisCache` captura los errores de Redis
  y del sistema operativo, registra una advertencia y se comporta como `NullCache` para esa
  llamada. Los tiempos de espera de conexión y de comando son de 0,5 s cada uno, por lo que
  una caída cuesta como máximo una demora breve por llamada al cache, no un error.
- Los errores lanzados al construir el valor (por ejemplo un not-found) se propagan y nunca
  se cachean.

Los scripts (`close_past_events`, `seed_demo`) construyen su propio cache de la misma
forma: Redis cuando `REDIS_URL` está definida, `NullCache` en caso contrario.

## Pruebas

| Archivo de pruebas | Cubre |
| --- | --- |
| `test_cache_policy.py` | Claves, resúmenes (digests), namespaces |
| `test_cached_reads.py` | Read-through y decoradores |
| `test_cached_events_api.py`, `test_cached_sessions_api.py`, `test_cached_speakers_api.py` | Comportamiento de los endpoints con un `FakeCache` |
| `test_cache_invalidation.py` | Qué operaciones descartan qué namespaces |
| `test_redis_cache.py` | Versionado y manejo de fallos con clientes fake |
| `test_cache_wiring.py`, `test_cache_settings.py` | Selección del adaptador y configuración de TTL |

Ninguna prueba necesita un Redis en ejecución: `FakeCache` y `UnreachableRedis` viven en
`backend/tests/fakes.py`.
