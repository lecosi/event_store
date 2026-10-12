"""Close past events: finish the published events whose end has already passed."""

from app.application.cache_policy import EventCache
from app.application.clock import Clock, utc_now
from app.application.ports import (
    EventRepository,
    UnitOfWork,
    transaction,
)
from app.domain.enums import EventStatus
from app.domain.event import validate_transition


def close_past_events(
    events: EventRepository,
    uow: UnitOfWork,
    cache: EventCache,
    clock: Clock = utc_now,
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
        cache.invalidate_with_sessions()
    return len(past)
