from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.csv_export import CSV_MEDIA_TYPE, session_participants_csv
from app.api.dependencies import get_clock, get_session_report_service, organizer_or_admin
from app.api.openapi_params import PageNumber, PageSize
from app.api.openapi_reports import SESSION_PARTICIPANTS_CSV_RESPONSES, SESSION_REPORT_ERRORS
from app.api.report_params import SessionParticipantFilters
from app.api.report_schemas import SessionParticipantPageResponse, SessionParticipantResponse
from app.application.clock import Clock
from app.application.report_filenames import session_participants_filename
from app.application.report_service import SessionReportService
from app.domain.user import UserAccount

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/sessions/participants",
    response_model=SessionParticipantPageResponse,
    summary="Preview the session participants report",
    responses=SESSION_REPORT_ERRORS,
)
def list_session_participants(
    params: SessionParticipantFilters,
    page: PageNumber = 1,
    size: PageSize = 10,
    user: UserAccount = Depends(organizer_or_admin),
    service: SessionReportService = Depends(get_session_report_service),
) -> SessionParticipantPageResponse:
    """Paginated list of people enrolled in sessions, with the session and its event.

    Requires the `organizer` or `admin` role (attendees get 403). Admins see the enrollments
    of every event; organizers only those of sessions of events they own, so a foreign
    `event_id` or `session_id` answers 403 and an unknown one 404. Filters combine with AND:
    `event_id`, `session_id`, `q` (session title or event name), `status` (event status) and
    `date_from` / `date_to` (session start date, UTC, both days included). Rows are ordered by
    session start, session, enrollment date and enrollment. Use the `.csv` variant with the
    same filters to download the whole result.
    """
    result = service.participants(user, params, page, size)
    return SessionParticipantPageResponse(
        items=[
            SessionParticipantResponse(
                full_name=row.full_name,
                email=row.email,
                event_name=row.event_name,
                session_title=row.session_title,
                session_start=row.session_start,
            )
            for row in result.items
        ],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get(
    "/sessions/participants.csv",
    response_class=StreamingResponse,
    summary="Download the session participants report as CSV",
    responses=SESSION_PARTICIPANTS_CSV_RESPONSES,
)
def export_session_participants(
    params: SessionParticipantFilters,
    user: UserAccount = Depends(organizer_or_admin),
    service: SessionReportService = Depends(get_session_report_service),
    clock: Clock = Depends(get_clock),
) -> StreamingResponse:
    """Download the session participants report as a CSV file generated on the fly.

    Same permissions, scope and filters as the JSON preview, without pagination: every
    matching enrollment is streamed in the same order. Access and filters are checked before
    the download starts, so authorization and validation errors are regular JSON errors.
    """
    rows = service.iter_participants(user, params)
    filename = session_participants_filename(params.session_id, clock)
    return StreamingResponse(
        session_participants_csv(rows),
        media_type=CSV_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
