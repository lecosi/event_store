from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import (
    get_current_user,
    get_registration_service,
    get_session_registration_service,
)
from app.api.event_schemas import (
    EventResponse,
    RegisteredEventPageResponse,
    RegisteredEventResponse,
    RegistrationResponse,
    SessionRegistrationResponse,
)
from app.api.openapi_params import EventId, PageNumber, PageSize, SessionId
from app.api.openapi_responses import (
    AUTHENTICATED,
    EVENT_NOT_FOUND,
    SESSION_NOT_FOUND,
    combine,
    conflict,
    conflicts,
    error_response,
)
from app.application.registration_service import RegistrationService
from app.application.session_registration_service import SessionRegistrationService
from app.domain.user import UserAccount

router = APIRouter(tags=["registrations"])


@router.post(
    "/events/{event_id}/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register to an event",
    responses=combine(
        AUTHENTICATED,
        EVENT_NOT_FOUND,
        conflict(
            "Already registered, the event is full, not published, or already ended.",
            "The event is full",
        ),
    ),
)
def register(
    event_id: EventId,
    user: UserAccount = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
) -> RegistrationResponse:
    """Register the authenticated user to an event. Any role.

    Rules: the event must be visible to the caller (otherwise 404), `published` and not yet
    ended, and have free spots. Conflicts (409): "You are already registered to this event",
    "The event is full", "Only published events accept registrations", "The event has
    already ended". Capacity is enforced atomically, so concurrent requests never oversell
    the last spot.
    """
    created = service.register(user, event_id)
    return RegistrationResponse(
        user_id=created.user_id, event_id=created.event_id, created_at=created.created_at
    )


@router.delete(
    "/events/{event_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel my registration",
    responses=combine(
        AUTHENTICATED,
        error_response(
            404,
            "The event does not exist, or the caller is not registered to it.",
            "You are not registered",
        ),
        conflict("The event is finished.", "A finished event does not allow cancelling"),
    ),
)
def unregister(
    event_id: EventId,
    user: UserAccount = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
) -> Response:
    """Cancel the authenticated user's registration, freeing the spot.

    404 if the event does not exist or the user is not registered; 409 once the event is
    `finished`.
    """
    service.cancel(user, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users/me/events",
    response_model=RegisteredEventPageResponse,
    summary="List my registered events",
    responses=AUTHENTICATED,
)
def my_events(
    page: PageNumber = 1,
    size: PageSize = 10,
    user: UserAccount = Depends(get_current_user),
    service: RegistrationService = Depends(get_registration_service),
) -> RegisteredEventPageResponse:
    """Paginated events the authenticated user is registered to, with the registration date."""
    result = service.my_events(user, page, size)
    return RegisteredEventPageResponse(
        items=[
            RegisteredEventResponse(
                **EventResponse.model_validate(r.event, from_attributes=True).model_dump(),
                registered_at=r.registered_at,
            )
            for r in result.items
        ],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.post(
    "/events/{event_id}/sessions/{session_id}/register",
    response_model=SessionRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a session",
    responses=combine(
        AUTHENTICATED,
        EVENT_NOT_FOUND,
        SESSION_NOT_FOUND,
        conflicts(
            "Already enrolled, not registered to the event, the session is full, the event is "
            "not published or has ended, the session has ended, or it overlaps another "
            "session of the caller.",
            {
                "full": ("The session is full", "The session is full"),
                "duplicate": ("Already enrolled", "You are already enrolled in this session"),
                "event_registration": (
                    "Not registered to the event",
                    "Register to the event before enrolling in a session",
                ),
                "overlap": (
                    "Schedule overlap",
                    "The session overlaps another session you are enrolled in",
                ),
            },
        ),
    ),
)
def enroll(
    event_id: EventId,
    session_id: SessionId,
    user: UserAccount = Depends(get_current_user),
    service: SessionRegistrationService = Depends(get_session_registration_service),
) -> SessionRegistrationResponse:
    """Enroll the authenticated user in a session of an event. Any role.

    Rules: the event must be visible to the caller (otherwise 404), `published` and not yet
    ended; the session must belong to the event and not have ended; the caller must already be
    registered to the event; the session must not overlap another session the caller is enrolled
    in (in any event); and it must have free seats (its own capacity). Capacity is enforced
    atomically, so concurrent requests never oversell the last seat.
    """
    created = service.enroll(user, event_id, session_id)
    return SessionRegistrationResponse(
        user_id=created.user_id, session_id=created.session_id, created_at=created.created_at
    )


@router.delete(
    "/events/{event_id}/sessions/{session_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel my session enrollment",
    responses=combine(
        AUTHENTICATED,
        EVENT_NOT_FOUND,
        error_response(
            404,
            "The event or session does not exist, or the caller is not enrolled in it.",
            "You are not enrolled in this session",
        ),
        conflict("The event is finished.", "A finished event does not allow cancelling"),
    ),
)
def unenroll(
    event_id: EventId,
    session_id: SessionId,
    user: UserAccount = Depends(get_current_user),
    service: SessionRegistrationService = Depends(get_session_registration_service),
) -> Response:
    """Cancel the authenticated user's enrollment in a session, freeing the seat.

    404 if the event or session does not exist or the user is not enrolled; 409 once the
    event is `finished`.
    """
    service.cancel(user, event_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
