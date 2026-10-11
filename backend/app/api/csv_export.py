"""CSV rendering of the participants report (streamed, never written to disk)."""

import csv
import io
from collections.abc import Iterable, Iterator

from app.domain.registration import ParticipantRow

BOM = "﻿"
DELIMITER = ";"
LINE_TERMINATOR = "\r\n"
HEADER = ("Nombre completo", "Correo electrónico", "Evento")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def neutralize(cell: str) -> str:
    """Prefix a quote so spreadsheets read cells starting with a formula trigger as text."""
    return f"'{cell}" if cell.startswith(FORMULA_PREFIXES) else cell


def participants_csv(rows: Iterable[ParticipantRow]) -> Iterator[str]:
    """Yield the file piece by piece: BOM and header first, then one line per participant."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator=LINE_TERMINATOR)

    def flush() -> str:
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    writer.writerow(HEADER)
    yield BOM + flush()
    for row in rows:
        writer.writerow([neutralize(v) for v in (row.full_name, row.email, row.event_name)])
        yield flush()
