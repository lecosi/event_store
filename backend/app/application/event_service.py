"""Event use cases. Depend only on ports and pure domain rules."""

from app.application.cache_policy import EventCache
from app.application.clock import Clock, utc_now
from app.application.errors import EventNotFoundError, PermissionDeniedError
from app.application.guards import EventAccessPolicy
from app.application.ports import (
    EventRepository,
    EventUsageQueries,
    UnitOfWork,
    transaction,
)
from app.domain.enums import EventStatus, Role
from app.domain.event import (
    Event,
    EventDetails,
    EventFilters,
    EventPage,
    can_view,
    ensure_capacity_covers_registrations,
    ensure_capacity_covers_sessions,
    ensure_dates_cover_sessions,
    ensure_editable,
    validate_details,
    validate_starts_in_future,
    validate_transition,
)
from app.domain.roles import ORGANIZING_ROLES
from app.domain.user import UserAccount


def is_public_view(viewer: UserAccount | None) -> bool:
    """Whether the viewer sees the same event list as an anonymous caller (published only).

    Only organizing roles can see non-published events in a list, so every other viewer
    shares the anonymous view and its results are safe to share between callers.
    """
    return viewer is None or viewer.role not in ORGANIZING_ROLES


class EventService:
    def __init__(
        self,
        events: EventRepository,
        usage: EventUsageQueries,
        uow: UnitOfWork,
        cache: EventCache,
        clock: Clock = utc_now,
    ) -> None:
        self._events = events
        self._access = EventAccessPolicy(events)
        self._usage = usage
        self._uow = uow
        self._cache = cache
        self._clock = clock

    def create(self, actor: UserAccount, details: EventDetails) -> Event:
        with transaction(self._uow):
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
            created = self._events.add(event)
        self._cache.invalidate()
        return created

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
            viewer_id=None if viewer is None or is_public_view(viewer) else viewer.id,
            unrestricted=viewer is not None and viewer.role is Role.ADMIN,
        )
        items, total = self._events.list_page(filters, page, size)
        return EventPage(items=items, total=total, page=page, size=size)

    def update(self, actor: UserAccount, event_id: int, details: EventDetails) -> Event:
        with transaction(self._uow):
            event = self.ensure_can_manage(actor, event_id)
            ensure_editable(event.status)
            validate_details(details)
            ensure_capacity_covers_sessions(
                details.capacity, self._usage.max_session_capacity(event_id)
            )
            ensure_capacity_covers_registrations(
                details.capacity, self._usage.count_registrations(event_id)
            )
            ensure_dates_cover_sessions(
                details.start_at, details.end_at, self._usage.session_bounds(event_id)
            )
            updated = self._events.update(event.with_details(details))
        self._cache.invalidate()
        return updated

    def change_status(self, actor: UserAccount, event_id: int, target: EventStatus) -> Event:
        with transaction(self._uow):
            event = self.ensure_can_manage(actor, event_id)
            validate_transition(event.status, target)
            event.status = target
            updated = self._events.update(event)
        self._cache.invalidate()
        return updated

    def delete(self, actor: UserAccount, event_id: int) -> None:
        with transaction(self._uow):
            self.ensure_can_manage(actor, event_id)
            self._events.delete(event_id)
        self._cache.invalidate_with_sessions()

    def ensure_can_manage(self, actor: UserAccount, event_id: int) -> Event:
        """Return the event when ``actor`` owns it or is an admin; raise otherwise."""
        return self._access.ensure_can_manage(actor, event_id)

    @staticmethod
    def _can_view(event: Event, viewer: UserAccount | None) -> bool:
        if viewer is None:
            return can_view(event, None, False)
        return can_view(event, viewer.id, viewer.role is Role.ADMIN)
