"""Download file names of the CSV reports; the date comes from an injected clock."""

from app.application.clock import Clock


def participants_filename(event_id: int | None, clock: Clock) -> str:
    if event_id is not None:
        return f"participantes_evento_{event_id}.csv"
    return f"participantes_{clock():%Y%m%d}.csv"


def session_participants_filename(session_id: int | None, clock: Clock) -> str:
    if session_id is not None:
        return f"participantes_sesion_{session_id}.csv"
    return f"participantes_sesiones_{clock():%Y%m%d}.csv"
