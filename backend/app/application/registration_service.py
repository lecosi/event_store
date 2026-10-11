"""Registration use cases. Depend only on ports and pure domain rules."""

from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial

from app.application.errors import EventNotFoundError
from app.application.ports import EventRepository, RegistrationRepository, UnitOfWork, transaction
from app.domain.enums import Role
from app.domain.event import Event, can_view
from app.domain.registration import (
    Availability,
    NotRegisteredError,
    RegisteredEventPage,
    Registration,
    available_spots,
    ensure_can_cancel,
    ensure_can_register,
)
from app.domain.user import UserAccount


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RegistrationService:
    def __init__(
        self,
        events: EventRepository,
        registrations: RegistrationRepository,
        uow: UnitOfWork,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._events = events
        self._registrations = registrations
        self._uow = uow
        self._clock = clock

    def register(self, user: UserAccount, event_id: int) -> Registration:
        assert user.id is not None
        with transaction(self._uow):
            self._get_visible(user, event_id)
            rule = partial(ensure_can_register, now=self._clock())
            return self._registrations.register(user.id, event_id, rule)

    def cancel(self, user: UserAccount, event_id: int) -> None:
        assert user.id is not None
        with transaction(self._uow):
            event = self._events.get(event_id)
            if event is None:
                raise EventNotFoundError(event_id)
            if not self._registrations.is_registered(user.id, event_id):
                raise NotRegisteredError
            ensure_can_cancel(event)
            self._registrations.cancel(user.id, event_id)

    def my_events(self, user: UserAccount, page: int = 1, size: int = 10) -> RegisteredEventPage:
        assert user.id is not None
        items, total = self._registrations.list_for_user(user.id, page, size)
        return RegisteredEventPage(items=items, total=total, page=page, size=size)

    def availability(self, event: Event, viewer: UserAccount | None) -> Availability:
        assert event.id is not None
        registered = self._events.count_registrations(event.id)
        is_registered = viewer is not None and self._registrations.is_registered(
            viewer.id or 0, event.id
        )
        return Availability(registered, available_spots(event.capacity, registered), is_registered)

    def _get_visible(self, user: UserAccount, event_id: int) -> Event:
        event = self._events.get(event_id)
        # Non-visible events look exactly like missing ones.
        if event is None or not can_view(event, user.id, user.role is Role.ADMIN):
            raise EventNotFoundError(event_id)
        return event
