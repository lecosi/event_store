from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    get_optional_user,
    get_session_catalogue,
    get_session_service,
    organizer_or_admin,
)
from app.api.openapi_params import EventId, SessionId
from app.api.openapi_responses import (
    EVENT_NOT_FOUND,
    ORGANIZER_OR_ADMIN,
    SESSION_NOT_FOUND,
    combine,
    conflict,
    conflicts,
)
from app.api.speaker_schemas import SessionRequest, SessionResponse
from app.application.session_catalogue import SessionCatalogue, SessionView
from app.application.session_service import SessionService
from app.domain.session import SessionDetails
from app.domain.user import UserAccount

router = APIRouter(prefix="/events/{event_id}/sessions", tags=["sessions"])


SESSION_CONFLICT = conflict(
    "The speaker has an overlapping session, or the event is cancelled or finished.",
    "the speaker already has a session in that time slot",
)

UPDATE_CONFLICT = conflicts(
    "The speaker has an overlapping session, the event is cancelled or finished, or the "
    "session has enrollments that the change would affect.",
    {
        "speaker_overlap": (
            "The speaker already has an overlapping session.",
            "the speaker already has a session in that time slot",
        ),
        "capacity_below_enrollments": (
            "The capacity is lower than the current enrollments.",
            "capacity cannot be lower than the current enrollments (3)",
        ),
        "schedule_locked": (
            "The session has enrollments and its dates changed.",
            "the schedule of a session with enrollments cannot be changed",
        ),
    },
)


def _details(body: SessionRequest) -> SessionDetails:
    return SessionDetails(**body.model_dump())


@router.get(
    "",
    response_model=list[SessionResponse],
    summary="List the sessions of an event",
    responses=EVENT_NOT_FOUND,
)
def list_sessions(
    event_id: EventId,
    viewer: UserAccount | None = Depends(get_optional_user),
    catalogue: SessionCatalogue = Depends(get_session_catalogue),
) -> list[SessionResponse]:
    """Sessions of an event with their speaker. Public; a token is optional.

    Follows the event visibility: sessions of a non-published event are only listed to its
    organizer and admins, anyone else gets 404.

    `enrolled_count`, `available_spots` and `is_enrolled` are computed per request, outside
    the cached schedule; `is_enrolled` is always false for anonymous callers.
    """
    return [SessionResponse.from_view(view) for view in catalogue.list_for_event(event_id, viewer)]


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a session to an event",
    responses=combine(ORGANIZER_OR_ADMIN, EVENT_NOT_FOUND, SESSION_CONFLICT),
)
def create_session(
    event_id: EventId,
    body: SessionRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """Schedule a session in an event. Only the event's organizer or an admin.

    Rules: the speaker must exist; the session must fit inside the event dates; its capacity is
    between 1 and the event capacity (422 otherwise). Conflicts (409): the event is `cancelled`
    or `finished`, or the speaker already has an overlapping session (sessions that merely
    touch, one ending when the next starts, do not overlap).
    """
    created = service.create(user, event_id, _details(body))
    return SessionResponse.from_view(SessionView.unenrolled(service.get_with_speaker(created)))


@router.put(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Update a session",
    responses=combine(ORGANIZER_OR_ADMIN, EVENT_NOT_FOUND, SESSION_NOT_FOUND, UPDATE_CONFLICT),
)
def update_session(
    event_id: EventId,
    session_id: SessionId,
    body: SessionRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: SessionService = Depends(get_session_service),
    catalogue: SessionCatalogue = Depends(get_session_catalogue),
) -> SessionResponse:
    """Replace a session. Only the event's organizer or an admin.

    Same rules as creating a session; the session keeps its own slot when checking for
    speaker overlaps. 404 when the session does not belong to the event. Once the session has
    enrollments, its capacity cannot go below the enrolled count and its dates cannot change
    (409); title and speaker stay editable.
    """
    updated = service.update(user, event_id, session_id, _details(body))
    item = service.get_with_speaker(updated)
    (view,) = catalogue.with_availability(event_id, [item], user)
    return SessionResponse.from_view(view)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    responses=combine(
        ORGANIZER_OR_ADMIN,
        EVENT_NOT_FOUND,
        SESSION_NOT_FOUND,
        conflicts(
            "The event is cancelled or finished, or the session has enrollments.",
            {
                "closed_event": (
                    "The event is cancelled or finished.",
                    "A finished event cannot be edited",
                ),
                "with_enrollments": (
                    "The session has enrollments.",
                    "a session with enrollments cannot be deleted",
                ),
            },
        ),
    ),
)
def delete_session(
    event_id: EventId,
    session_id: SessionId,
    user: UserAccount = Depends(organizer_or_admin),
    service: SessionService = Depends(get_session_service),
) -> Response:
    """Remove a session from an event. Only the event's organizer or an admin."""
    service.delete(user, event_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
