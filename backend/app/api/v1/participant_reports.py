from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.csv_export import CSV_MEDIA_TYPE, participants_csv
from app.api.dependencies import get_clock, get_report_service, organizer_or_admin
from app.api.openapi_params import PageNumber, PageSize
from app.api.openapi_reports import PARTICIPANTS_CSV_RESPONSES, REPORT_ERRORS
from app.api.report_params import ParticipantFilters
from app.api.report_schemas import ParticipantPageResponse, ParticipantResponse
from app.application.clock import Clock
from app.application.report_filenames import participants_filename
from app.application.report_service import ReportService
from app.domain.user import UserAccount

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/participants",
    response_model=ParticipantPageResponse,
    summary="Preview the participants report",
    responses=REPORT_ERRORS,
)
def list_participants(
    params: ParticipantFilters,
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
    responses=PARTICIPANTS_CSV_RESPONSES,
)
def export_participants(
    params: ParticipantFilters,
    user: UserAccount = Depends(organizer_or_admin),
    service: ReportService = Depends(get_report_service),
    clock: Clock = Depends(get_clock),
) -> StreamingResponse:
    """Download the participants report as a CSV file generated on the fly.

    Same permissions, scope and filters as the JSON preview, without pagination: every
    matching participant is streamed in the same order. Access and filters are checked before
    the download starts, so authorization and validation errors are regular JSON errors.
    """
    rows = service.iter_participants(user, params)
    filename = participants_filename(params.event_id, clock)
    return StreamingResponse(
        participants_csv(rows),
        media_type=CSV_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
