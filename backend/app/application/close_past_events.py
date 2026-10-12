"""Close past events: finish the published events whose end has already passed."""

from app.application.clock import Clock, utc_now
from app.application.ports import (
    EVENTS_NAMESPACE,
    SESSIONS_NAMESPACE,
    Cache,
    EventRepository,
    NullCache,
    UnitOfWork,
    transaction,
)
from app.domain.enums import EventStatus
from app.domain.event import validate_transition


def close_past_events(
    events: EventRepository,
    uow: UnitOfWork,
    clock: Clock = utc_now,
    cache: Cache | None = None,
) -> int:
    """Move every PUBLISHED event with ``end_at`` before now to FINISHED; return how many.

    Events still in progress, drafts, cancelled and finished events are left alone, and
    registrations and session enrollments are kept as the attendance history. Running it again
    finds nothing left to close.
    """
    with transaction(uow):
        past = events.list_published_ended_before(clock())
        for event in past:
            validate_transition(event.status, EventStatus.FINISHED)
            event.status = EventStatus.FINISHED
            events.update(event)
    if past:
        active_cache: Cache = cache if cache is not None else NullCache()
        active_cache.invalidate(EVENTS_NAMESPACE)
        active_cache.invalidate(SESSIONS_NAMESPACE)
    return len(past)
