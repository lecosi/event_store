# Backend scripts

Run them from `backend/` (or inside the backend container, where `scripts/` is shipped):

```bash
python -m scripts.seed                # create or promote the administrator
python -m scripts.close_past_events   # finish published events that already ended
```

## Finish past events

`python -m scripts.close_past_events` moves every `published` event whose end date is
before now to `finished`, and prints `Finished events: <n>`.

- Events still in progress, drafts, cancelled and already finished events are not touched.
- Registrations and session enrollments are kept as the attendance history.
- It is idempotent: running it again finishes nothing new.
- It invalidates the events and sessions read cache when it finishes at least one event.

It uses the same `DATABASE_URL` (and `REDIS_URL`, if set) as the API. Nothing runs it
automatically, so schedule it. Example crontab entry, every day at 02:00:

```cron
0 2 * * * cd /srv/mis-eventos && docker compose exec -T backend python -m scripts.close_past_events
```
