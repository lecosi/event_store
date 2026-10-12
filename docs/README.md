# Documentación

Índice de la documentación del proyecto, en el orden de lectura sugerido. Los documentos
del backend describen el código tal como está hoy y referencian los archivos reales.

## Empieza aquí

| Documento | Qué cubre |
| --- | --- |
| [../README.md](../README.md) | Qué es el proyecto y cómo ejecutarlo con unos pocos comandos |
| [screens.md](screens.md) | Pantallas de la aplicación, con capturas |

## Backend: para entenderlo

| Documento | Qué cubre |
| --- | --- |
| [backend-architecture.md](backend-architecture.md) | Capas hexagonales, puertos y adaptadores, unidad de trabajo, dónde se ensamblan las dependencias, mapeo de errores, una petición de extremo a extremo, ejemplos de SOLID |
| [backend-domain-rules.md](backend-domain-rules.md) | Reglas de negocio: roles, ciclo de vida del evento, inscripciones, inscripciones a sesiones, ponentes, reportes y CSV, administración de usuarios |
| [backend-api.md](backend-api.md) | Resumen de endpoints por tag, autenticación, formato de errores, paginación |
| [backend-cache.md](backend-cache.md) | Qué se cachea, claves, TTL, invalidación, comportamiento sin Redis |

## Backend: para trabajar con él

| Documento | Qué cubre |
| --- | --- |
| [backend-testing.md](backend-testing.md) | Ejecución de pruebas, fakes frente a PostgreSQL, cobertura, lint y verificación de tipos |
| [backend-operations.md](backend-operations.md) | Docker Compose, variables de entorno, migraciones, carga inicial de datos (seed) |
| [backend-scripts.md](backend-scripts.md) | Scripts `seed`, `seed_demo` y `close_past_events`, programación de ejecución |
| [coverage/README.md](coverage/README.md) | Resúmenes de cobertura de pruebas y cómo regenerar los reportes |

## Frontend

| Documento | Qué cubre |
| --- | --- |
| [frontend-architecture.md](frontend-architecture.md) | Mapa de `frontend/src`, una pantalla de extremo a extremo, rutas y protección por rol, sesión, cliente HTTP y traducción de errores |
| [frontend-conventions.md](frontend-conventions.md) | Textos en español con i18n, validaciones frente al backend, estilos y componentes compartidos, cómo agregar una pantalla |
| [frontend-operations.md](frontend-operations.md) | Scripts npm, Docker y nginx, conexión con el backend, pruebas, cobertura, lint y formato |

## Qué documento para qué pregunta

- "¿Cómo está construido y por qué?" -> architecture, luego domain rules.
- "¿Qué puede hacer este endpoint y quién puede llamarlo?" -> API, luego domain rules.
- "¿Cómo lo ejecuto o lo despliego?" -> operations, luego scripts.
- "¿Cómo agrego una funcionalidad de forma segura?" -> architecture (capas y puertos), testing.
