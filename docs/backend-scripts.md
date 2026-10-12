# Scripts del backend

Ejecútalos desde `backend/` (o dentro del contenedor del backend, donde se incluye
`scripts/`):

```bash
python -m scripts.seed                # create or promote the administrator
python -m scripts.seed_demo           # optional demo data, needs the administrator
python -m scripts.close_past_events   # finish published events that already ended
```

`seed` lee `ADMIN_EMAIL` y `ADMIN_PASSWORD` (y `ADMIN_FULL_NAME`, por defecto
`Administrator`); `seed_demo` lee `ADMIN_EMAIL`. Ejecútalos una vez que el backend esté
saludable, para que las migraciones ya estén aplicadas. Ver
[backend-operations.md](backend-operations.md#carga-inicial-de-datos-seed).

## Finalizar eventos pasados

`python -m scripts.close_past_events` mueve a `finished` todo evento `published` cuya fecha
de fin es anterior al momento actual, e imprime `Finished events: <n>`.

- Los eventos aún en curso, los borradores, los cancelados y los ya finalizados no se
  tocan.
- Las inscripciones y las inscripciones a sesiones se conservan como historial de
  asistencia.
- Es idempotente: ejecutarlo de nuevo no finaliza nada nuevo.
- Invalida el cache de lectura de eventos y sesiones cuando finaliza al menos un evento.

Usa el mismo `DATABASE_URL` (y `REDIS_URL`, si está definida) que la API. Nada lo ejecuta
automáticamente, así que prográmalo. Ejemplo de entrada de crontab, todos los días a las
02:00:

```cron
0 2 * * * cd /srv/mis-eventos && docker compose exec -T backend python -m scripts.close_past_events
```
