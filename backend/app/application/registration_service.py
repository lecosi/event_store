"""Registration use cases. Depend only on ports and pure domain rules."""

from functools import partial

from app.application.clock import Clock, utc_now
from app.application.guards import EventAccessPolicy, get_event
from app.application.ports import (
    EventRepository,
    EventUsageQueries,
    RegistrationRepository,
    SessionEnrollmentWriter,
    UnitOfWork,
    transaction,
)
from app.domain.event import Event
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


class RegistrationService:
    def __init__(
        self,
        events: EventRepository,
        usage: EventUsageQueries,
        registrations: RegistrationRepository,
        enrollments: SessionEnrollmentWriter,
        uow: UnitOfWork,
        clock: Clock = utc_now,
    ) -> None:
        self._events = events
        self._access = EventAccessPolicy(events)
        self._usage = usage
        self._registrations = registrations
        self._enrollments = enrollments
        self._uow = uow
        self._clock = clock

    def register(self, user: UserAccount, event_id: int) -> Registration:
        assert user.id is not None
        with transaction(self._uow):
            self._access.get_visible(user, event_id)
            rule = partial(ensure_can_register, now=self._clock())
            return self._registrations.register(user.id, event_id, rule)

    def cancel(self, user: UserAccount, event_id: int) -> None:
        """Cancel the registration and the user's enrollments in the event's sessions.

        The registration is deleted first: that delete waits for a concurrent enrollment
        holding its row lock, so the enrollments removed afterwards include that one.
        """
        assert user.id is not None
        with transaction(self._uow):
            event = get_event(self._events, event_id)
            if not self._registrations.is_registered(user.id, event_id):
                raise NotRegisteredError
            ensure_can_cancel(event)
            self._registrations.cancel(user.id, event_id)
            self._enrollments.cancel_for_event(user.id, event_id)

    def my_events(self, user: UserAccount, page: int = 1, size: int = 10) -> RegisteredEventPage:
        assert user.id is not None
        items, total = self._registrations.list_for_user(user.id, page, size)
        return RegisteredEventPage(items=items, total=total, page=page, size=size)

    def availability(self, event: Event, viewer: UserAccount | None) -> Availability:
        assert event.id is not None
        registered = self._usage.count_registrations(event.id)
        is_registered = viewer is not None and self._registrations.is_registered(
            viewer.id or 0, event.id
        )
        return Availability(registered, available_spots(event.capacity, registered), is_registered)
