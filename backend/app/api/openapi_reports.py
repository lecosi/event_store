"""OpenAPI fragments of the report endpoints: CSV examples, error examples and CSV responses."""

from app.api.openapi_responses import (
    EVENT_NOT_FOUND,
    ORGANIZER_OR_ADMIN,
    ValidationErrorResponse,
    combine,
    error_examples,
)

CSV_EXAMPLE = (
    "﻿Nombre completo;Correo electrónico;Evento\r\n"
    "Ana Gomez;ana.gomez@example.com;PyCon Latam 2030\r\n"
    "Luis Perez;luis.perez@example.com;PyCon Latam 2030\r\n"
)
SESSION_CSV_EXAMPLE = (
    "﻿Nombre completo;Correo electrónico;Evento;Sesión;Inicio de la sesión\r\n"
    "Ana Gomez;ana.gomez@example.com;PyCon Latam 2030;Keynote;2030-05-10T09:00:00Z\r\n"
)
DATE_RANGE_DETAIL = "date_to must not be before date_from"


def _unprocessable(description: str) -> dict[int | str, dict[str, object]]:
    return {
        422: {
            "model": ValidationErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_parameter": {
                            "summary": "A parameter has an invalid value",
                            "value": {
                                "detail": [
                                    {
                                        "loc": ["query", "date_from"],
                                        "msg": "Input should be a valid date or datetime, "
                                        "invalid character in year",
                                        "type": "date_from_datetime_parsing",
                                    }
                                ]
                            },
                        },
                        "invalid_date_range": {
                            "summary": "date_to is before date_from",
                            "value": {"detail": DATE_RANGE_DETAIL},
                        },
                    }
                }
            },
        }
    }


REPORT_ERRORS = combine(
    ORGANIZER_OR_ADMIN,
    EVENT_NOT_FOUND,
    _unprocessable(
        "A parameter is malformed or out of range, or `date_to` is before `date_from`. "
        "Malformed parameters answer with a list of field errors; the date range rule "
        "answers with a message."
    ),
)


SESSION_REPORT_ERRORS = combine(
    REPORT_ERRORS,
    error_examples(
        404,
        "The event or the session does not exist.",
        {
            "event": ("Unknown event_id", "Event not found"),
            "session": ("Unknown session_id", "Session not found"),
        },
    ),
)


PARTICIPANTS_CSV_RESPONSES = combine(
    {
        200: {
            "description": (
                "CSV file, UTF-8 with BOM, `;` separated, CRLF line ends. Columns: "
                "`Nombre completo`, `Correo electrónico`, `Evento`. Cells that start with "
                "`=`, `+`, `-`, `@`, tab or carriage return are prefixed with `'` so "
                "spreadsheets do not run them as formulas. Only the header row is sent "
                "when nothing matches."
            ),
            "headers": {
                "Content-Disposition": {
                    "description": (
                        '`attachment; filename="participantes_<YYYYMMDD>.csv"`, or '
                        "`participantes_evento_<event_id>.csv` when `event_id` is given."
                    ),
                    "schema": {"type": "string"},
                },
                "Cache-Control": {
                    "description": "Always `no-store`.",
                    "schema": {"type": "string"},
                },
            },
            "content": {
                "text/csv": {
                    "schema": {"type": "string", "format": "binary"},
                    "example": CSV_EXAMPLE,
                }
            },
        }
    },
    REPORT_ERRORS,
)

SESSION_PARTICIPANTS_CSV_RESPONSES = combine(
    {
        200: {
            "description": (
                "CSV file, UTF-8 with BOM, `;` separated, CRLF line ends. Columns: "
                "`Nombre completo`, `Correo electrónico`, `Evento`, `Sesión`, "
                "`Inicio de la sesión` (ISO 8601, UTC). Cells that start with `=`, `+`, "
                "`-`, `@`, tab or carriage return are prefixed with `'` so spreadsheets "
                "do not run them as formulas. Only the header row is sent when nothing "
                "matches."
            ),
            "headers": {
                "Content-Disposition": {
                    "description": (
                        '`attachment; filename="participantes_sesiones_<YYYYMMDD>.csv"`, '
                        "or `participantes_sesion_<session_id>.csv` when `session_id` is "
                        "given."
                    ),
                    "schema": {"type": "string"},
                },
                "Cache-Control": {
                    "description": "Always `no-store`.",
                    "schema": {"type": "string"},
                },
            },
            "content": {
                "text/csv": {
                    "schema": {"type": "string", "format": "binary"},
                    "example": SESSION_CSV_EXAMPLE,
                }
            },
        }
    },
    SESSION_REPORT_ERRORS,
)
