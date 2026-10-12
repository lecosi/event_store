# Documentación

**Mis Eventos** es una aplicación web para gestionar eventos de principio a fin: desde
que un organizador los crea hasta que los asistentes se inscriben. Nace para resolver
cuatro problemas: la desorganización, los procesos manuales (inscripciones y reportes),
las decisiones tomadas sin información y una experiencia de usuario deficiente.

Qué permite hacer cada rol dentro de **Mis Eventos**:

- **Asistente:** buscar eventos por nombre, ver el detalle con sus sesiones, inscribirse
  al evento y a sesiones concretas mientras haya cupo, y consultar sus inscripciones.
- **Organizador:** crear y administrar eventos con estados, capacidad, sesiones y
  ponentes, y exportar reportes de participantes en CSV.
- **Administrador:** gestionar usuarios y roles.

Las cuentas creadas desde el formulario de registro siempre son de organizador
(`POST /auth/register`, rol por defecto en `backend/app/application/auth_service.py`). El
rol de asistente se obtiene de dos formas: un administrador cambia el rol en la pantalla
de administración de usuarios (`/admin/users`), o se usan los usuarios de demostración que
crea `backend/scripts/seed_demo.py` (`attendee@example.com` y `attendee1@example.com` a
`attendee4@example.com`, con la contraseña `attendee123`).

## Empieza aquí

| Documento | Qué cubre |
| --- | --- |
| [../README.md](../README.md) | Qué es el proyecto y cómo ejecutarlo con unos pocos comandos |
| [screens.md](screens.md) | Pantallas de la aplicación, con capturas |
| [../backend/README.md](../backend/README.md) | Cómo configurar, ejecutar y probar el backend |
| [../frontend/README.md](../frontend/README.md) | Cómo configurar, ejecutar y probar el frontend |

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
