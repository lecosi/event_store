"""Event use cases. Depend only on ports and pure domain rules."""

from collections.abc import Callable
from datetime import UTC, datetime

from app.application.errors import EventNotFoundError, PermissionDeniedError
from app.application.ports import EventRepository
from app.domain.enums import EventStatus, Role
from app.domain.event import (
    Event,
    EventDetails,
    EventFilters,
    EventPage,
    can_view,
    ensure_capacity_covers_sessions,
    ensure_dates_cover_sessions,
    ensure_editable,
    validate_details,
    validate_starts_in_future,
    validate_transition,
)
from app.domain.user import UserAccount

ORGANIZING_ROLES = (Role.ORGANIZER, Role.ADMIN)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EventService:
    def __init__(self, events: EventRepository, clock: Callable[[], datetime] = _utcnow) -> None:
        self._events = events
        self._clock = clock

    def create(self, actor: UserAccount, details: EventDetails) -> Event:
        if actor.role not in ORGANIZING_ROLES:
            raise PermissionDeniedError
        validate_details(details)
        validate_starts_in_future(details.start_at, self._clock())
        assert actor.id is not None
        event = Event(
            name=details.name,
            description=details.description,
            location=details.location,
            start_at=details.start_at,
            end_at=details.end_at,
            capacity=details.capacity,
            organizer_id=actor.id,
        )
        return self._events.add(event)

    def get(self, event_id: int, viewer: UserAccount | None) -> Event:
        event = self._events.get(event_id)
        # Non-visible events look exactly like missing ones.
        if event is None or not self._can_view(event, viewer):
            raise EventNotFoundError(event_id)
        return event

    def list(
        self,
        viewer: UserAccount | None,
        q: str | None = None,
        status: EventStatus | None = None,
        page: int = 1,
        size: int = 10,
    ) -> EventPage:
        filters = EventFilters(
            q=q.strip() if q and q.strip() else None,
            status=status,
            viewer_id=viewer.id if viewer else None,
            unrestricted=viewer is not None and viewer.role is Role.ADMIN,
        )
        items, total = self._events.list_page(filters, page, size)
        return EventPage(items=items, total=total, page=page, size=size)

    def update(self, actor: UserAccount, event_id: int, details: EventDetails) -> Event:
        event = self._get_managed(actor, event_id)
        ensure_editable(event.status)
        validate_details(details)
        ensure_capacity_covers_sessions(
            details.capacity, self._events.max_session_capacity(event_id)
        )
        ensure_dates_cover_sessions(
            details.start_at, details.end_at, self._events.session_bounds(event_id)
        )
        return self._events.update(event.with_details(details))

    def change_status(self, actor: UserAccount, event_id: int, target: EventStatus) -> Event:
        event = self._get_managed(actor, event_id)
        validate_transition(event.status, target)
        event.status = target
        return self._events.update(event)

    def delete(self, actor: UserAccount, event_id: int) -> None:
        self._get_managed(actor, event_id)
        self._events.delete(event_id)

    def _get_managed(self, actor: UserAccount, event_id: int) -> Event:
        event = self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        if actor.role is not Role.ADMIN and event.organizer_id != actor.id:
            raise PermissionDeniedError
        return event

    @staticmethod
    def _can_view(event: Event, viewer: UserAccount | None) -> bool:
        if viewer is None:
            return can_view(event, None, False)
        return can_view(event, viewer.id, viewer.role is Role.ADMIN)
