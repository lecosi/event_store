from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.csv_export import participants_csv
from app.api.dependencies import get_report_service, require_role
from app.api.openapi_params import PageNumber, PageSize
from app.api.openapi_responses import (
    EVENT_NOT_FOUND,
    ORGANIZER_OR_ADMIN,
    ValidationErrorResponse,
    combine,
)
from app.api.report_schemas import ParticipantPageResponse, ParticipantResponse
from app.application.clock import utc_now
from app.application.report_service import ParticipantParams, ReportService
from app.domain.enums import EventStatus, Role
from app.domain.user import UserAccount

router = APIRouter(prefix="/reports", tags=["reports"])

organizer_or_admin = require_role(Role.ORGANIZER, Role.ADMIN)

CSV_MEDIA_TYPE = "text/csv; charset=utf-8"
CSV_EXAMPLE = (
    "﻿Nombre completo;Correo electrónico;Evento\r\n"
    "Ana Gomez;ana.gomez@example.com;PyCon Latam 2030\r\n"
    "Luis Perez;luis.perez@example.com;PyCon Latam 2030\r\n"
)
DATE_RANGE_DETAIL = "date_to must not be before date_from"


def participant_params(
    event_id: Annotated[
        int | None,
        Query(
            description=(
                "Only participants of this event. Organizers can only use their own events "
                "(403 otherwise); an unknown event answers 404."
            ),
            examples=[1],
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Case-insensitive text to look for in the event name (participant names are "
                "not searched)."
            ),
            examples=["python"],
        ),
    ] = None,
    status_filter: Annotated[
        EventStatus | None,
        Query(
            alias="status",
            description="Only participants of events in this status.",
            examples=["published"],
        ),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(
            description=(
                "First day (inclusive, UTC) of the event start date range, as `YYYY-MM-DD`."
            ),
            examples=["2030-05-01"],
        ),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(
            description=(
                "Last day (inclusive, UTC, until 23:59:59.999999) of the event start date "
                "range, as `YYYY-MM-DD`. It must not be before `date_from` (422)."
            ),
            examples=["2030-05-31"],
        ),
    ] = None,
) -> ParticipantParams:
    return ParticipantParams(
        event_id=event_id, q=q, status=status_filter, date_from=date_from, date_to=date_to
    )


Filters = Annotated[ParticipantParams, Depends(participant_params)]


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


@router.get(
    "/participants",
    response_model=ParticipantPageResponse,
    summary="Preview the participants report",
    responses=REPORT_ERRORS,
)
def list_participants(
    params: Filters,
    page: PageNumber = 1,
    size: PageSize = 10,
    user: UserAccount = Depends(organizer_or_admin),
    service: ReportService = Depends(get_report_service),
) -> ParticipantPageResponse:
    """Paginated list of registered people with the event they registered to.

    Requires the `organizer` or `admin` role (attendees get 403). Admins see the participants
    of every event; organizers only those of events they own, so a foreign `event_id` answers
    403 and an unknown one 404. Filters combine with AND: `event_id`, `q` (event name),
    `status` (event status) and `date_from` / `date_to` (event start date, UTC, both days
    included). Rows are ordered by event start, event, registration date and registration;
    cancelled registrations do not appear. Use the `.csv` variant with the same filters to
    download the whole result.
    """
    result = service.participants(user, params, page, size)
    return ParticipantPageResponse(
        items=[
            ParticipantResponse(full_name=row.full_name, email=row.email, event_name=row.event_name)
            for row in result.items
        ],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get(
    "/participants.csv",
    response_class=StreamingResponse,
    summary="Download the participants report as CSV",
    responses=combine(
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
    ),
)
def export_participants(
    params: Filters,
    user: UserAccount = Depends(organizer_or_admin),
    service: ReportService = Depends(get_report_service),
) -> StreamingResponse:
    """Download the participants report as a CSV file generated on the fly.

    Same permissions, scope and filters as the JSON preview, without pagination: every
    matching participant is streamed in the same order. Access and filters are checked before
    the download starts, so authorization and validation errors are regular JSON errors.
    """
    rows = service.iter_participants(user, params)
    filename = (
        f"participantes_evento_{params.event_id}.csv"
        if params.event_id is not None
        else f"participantes_{utc_now():%Y%m%d}.csv"
    )
    return StreamingResponse(
        participants_csv(rows),
        media_type=CSV_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
