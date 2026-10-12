"""CSV rendering of the participants report (streamed, never written to disk)."""

import csv
import io
from collections.abc import Iterable, Iterator

from app.domain.event import ensure_utc
from app.domain.registration import ParticipantRow
from app.domain.session_registration import SessionParticipantRow

BOM = "﻿"
DELIMITER = ";"
LINE_TERMINATOR = "\r\n"
HEADER = ("Nombre completo", "Correo electrónico", "Evento")
SESSION_HEADER = (*HEADER, "Sesión", "Inicio de la sesión")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralize(cell: str) -> str:
    """Prefix a quote so spreadsheets read cells starting with a formula trigger as text."""
    return f"'{cell}" if cell.startswith(FORMULA_PREFIXES) else cell


def _stream(header: tuple[str, ...], rows: Iterable[Iterable[str]]) -> Iterator[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator=LINE_TERMINATOR)

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    writer.writerow(header)
    yield BOM + flush()
    for row in rows:
        writer.writerow([neutralize(cell) for cell in row])
        yield flush()


def participants_csv(rows: Iterable[ParticipantRow]) -> Iterator[str]:
    """Yield the file piece by piece: BOM and header first, then one line per participant."""
    return _stream(HEADER, ((row.full_name, row.email, row.event_name) for row in rows))


def session_participants_csv(rows: Iterable[SessionParticipantRow]) -> Iterator[str]:
    """Same streaming as ``participants_csv`` with the session columns; start is ISO 8601 UTC."""
    return _stream(
        SESSION_HEADER,
        (
            (
                row.full_name,
                row.email,
                row.event_name,
                row.session_title,
                ensure_utc(row.session_start).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            for row in rows
        ),
    )
