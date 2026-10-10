from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.dependencies import (
    get_event_service,
    get_optional_user,
    get_registration_service,
    get_session_service,
    require_role,
)
from app.api.event_schemas import (
    EventDetailResponse,
    EventPageResponse,
    EventRequest,
    EventResponse,
    EventStatusRequest,
)
from app.api.openapi_params import EventId, PageNumber, PageSize
from app.api.openapi_responses import (
    EVENT_NOT_FOUND,
    ORGANIZER_OR_ADMIN,
    combine,
    conflict,
)
from app.api.speaker_schemas import SessionResponse
from app.application.errors import EventNotFoundError, PermissionDeniedError
from app.application.event_service import EventService
from app.application.registration_service import RegistrationService
from app.application.session_service import SessionService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventDetails, EventStateError, EventValidationError
from app.domain.user import UserAccount

router = APIRouter(prefix="/events", tags=["events"])

organizer_or_admin = require_role(Role.ORGANIZER, Role.ADMIN)


def _details(body: EventRequest) -> EventDetails:
    return EventDetails(**body.model_dump())


def _detail(
    event: Event,
    sessions: SessionService,
    registrations: RegistrationService,
    viewer: UserAccount | None,
) -> EventDetailResponse:
    base = EventResponse.model_validate(event, from_attributes=True)
    items = [SessionResponse.from_domain(s) for s in sessions.list_for_event(event.id)]
    availability = registrations.availability(event, viewer)
    return EventDetailResponse(**base.model_dump(), sessions=items, **asdict(availability))


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, EventNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")
    if isinstance(exc, PermissionDeniedError):
        return HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    if isinstance(exc, EventValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, EventStateError):
        return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    raise exc


HANDLED = (EventNotFoundError, PermissionDeniedError, EventValidationError, EventStateError)


@router.post(
    "",
    response_model=EventDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an event",
    responses=ORGANIZER_OR_ADMIN,
)
def create_event(
    body: EventRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: EventService = Depends(get_event_service),
    sessions: SessionService = Depends(get_session_service),
    registrations: RegistrationService = Depends(get_registration_service),
) -> EventDetailResponse:
    """Create an event owned by the caller. Requires the `organizer` or `admin` role.

    The event starts in `draft` status (not public until published). Business rules (422):
    `start_at` must be in the future, `end_at` after `start_at`, and `capacity` at least 1.
    """
    try:
        return _detail(service.create(user, _details(body)), sessions, registrations, user)
    except HANDLED as exc:
        raise _translate(exc) from exc


@router.get("", response_model=EventPageResponse, summary="Search and list events")
def list_events(
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Case-insensitive text to look for in the event name "
                "(descriptions are not searched)."
            ),
            examples=["python"],
        ),
    ] = None,
    status_filter: Annotated[
        EventStatus | None,
        Query(
            alias="status",
            description=(
                "Only events in this status. Non-admin callers still only see published "
                "events plus their own."
            ),
            examples=["published"],
        ),
    ] = None,
    page: PageNumber = 1,
    size: PageSize = 10,
    viewer: UserAccount | None = Depends(get_optional_user),
    service: EventService = Depends(get_event_service),
) -> EventPageResponse:
    """Paginated event catalogue. Public; a token is optional.

    Visibility: anonymous users and attendees see only `published` events; organizers also see
    their own events in any status; admins see everything. Combine `q` (text search) and
    `status` to filter, and `page`/`size` to paginate.
    """
    result = service.list(viewer, q=q, status=status_filter, page=page, size=size)
    return EventPageResponse(
        items=[EventResponse.model_validate(e, from_attributes=True) for e in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get(
    "/{event_id}",
    response_model=EventDetailResponse,
    summary="Get an event",
    responses=EVENT_NOT_FOUND,
)
def get_event(
    event_id: EventId,
    viewer: UserAccount | None = Depends(get_optional_user),
    service: EventService = Depends(get_event_service),
    sessions: SessionService = Depends(get_session_service),
    registrations: RegistrationService = Depends(get_registration_service),
) -> EventDetailResponse:
    """Event detail with its sessions, registered count and available spots. Public.

    Non-published events are only visible to their organizer and admins; for anyone else they
    answer 404, exactly as if they did not exist. With a token, `is_registered` tells whether
    the caller is registered.
    """
    try:
        return _detail(service.get(event_id, viewer), sessions, registrations, viewer)
    except HANDLED as exc:
        raise _translate(exc) from exc


@router.put(
    "/{event_id}",
    response_model=EventDetailResponse,
    summary="Update an event",
    responses=combine(
        ORGANIZER_OR_ADMIN,
        EVENT_NOT_FOUND,
        conflict(
            "The event cannot be edited in its state or the new values contradict existing data.",
            "capacity cannot be lower than the current registrations (3)",
        ),
    ),
)
def update_event(
    event_id: EventId,
    body: EventRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: EventService = Depends(get_event_service),
    sessions: SessionService = Depends(get_session_service),
    registrations: RegistrationService = Depends(get_registration_service),
) -> EventDetailResponse:
    """Replace the editable fields of an event. Only its organizer or an admin.

    Conflicts (409): `cancelled` and `finished` events cannot be edited; `capacity` cannot be
    lower than the current registrations or than the largest session; the new dates must still
    contain every existing session. Invalid dates or capacity answer 422.
    """
    try:
        return _detail(
            service.update(user, event_id, _details(body)), sessions, registrations, user
        )
    except HANDLED as exc:
        raise _translate(exc) from exc


@router.patch(
    "/{event_id}/status",
    response_model=EventDetailResponse,
    summary="Change the status of an event",
    responses=combine(
        ORGANIZER_OR_ADMIN,
        EVENT_NOT_FOUND,
        conflict(
            "The requested transition is not allowed from the current status.",
            "Cannot change status from cancelled to published",
        ),
    ),
)
def change_event_status(
    event_id: EventId,
    body: EventStatusRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: EventService = Depends(get_event_service),
    sessions: SessionService = Depends(get_session_service),
    registrations: RegistrationService = Depends(get_registration_service),
) -> EventDetailResponse:
    """Move an event through its lifecycle. Only its organizer or an admin.

    Status values: `draft` (default, hidden), `published` (public, accepts registrations),
    `cancelled` and `finished` (final).

    Allowed transitions:

    - `draft` -> `published` or `cancelled`
    - `published` -> `finished` or `cancelled`
    - `cancelled` and `finished` -> none

    Any other transition answers 409.
    """
    try:
        return _detail(
            service.change_status(user, event_id, body.status), sessions, registrations, user
        )
    except HANDLED as exc:
        raise _translate(exc) from exc


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event",
    responses=combine(ORGANIZER_OR_ADMIN, EVENT_NOT_FOUND),
)
def delete_event(
    event_id: EventId,
    user: UserAccount = Depends(organizer_or_admin),
    service: EventService = Depends(get_event_service),
) -> Response:
    """Permanently delete an event and its sessions. Only its organizer or an admin."""
    try:
        service.delete(user, event_id)
    except HANDLED as exc:
        raise _translate(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
