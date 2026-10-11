from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_current_user, get_registration_service
from app.api.event_schemas import (
    EventResponse,
    RegisteredEventPageResponse,
    RegisteredEventResponse,
    RegistrationResponse,
)
from app.api.openapi_params import EventId, PageNumber, PageSize
from app.api.openapi_responses import (
    AUTHENTICATED,
    EVENT_NOT_FOUND,
    combine,
    conflict,
    error_response,
)
from app.application.registration_service import RegistrationService
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
