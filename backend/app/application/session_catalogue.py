"""Read-side use case: the sessions of an event with the seats left and the viewer enrollment."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.application.ports import SessionAvailabilityReader
from app.application.readers import EventLookup, EventSchedule
from app.domain.registration import available_spots
from app.domain.session import SessionWithSpeaker
from app.domain.session_registration import SessionAvailability
from app.domain.user import UserAccount


@dataclass(frozen=True)
class SessionView:
    """A scheduled session together with the availability seen by one viewer."""

    session: SessionWithSpeaker
    availability: SessionAvailability

    @classmethod
    def unenrolled(cls, item: SessionWithSpeaker) -> "SessionView":
        capacity = item.session.capacity
        return cls(item, SessionAvailability(0, available_spots(capacity, 0), False))


class SessionCatalogue:
    """Merges the shareable schedule with per-viewer availability, which is always read live."""

    def __init__(
        self,
        events: EventLookup,
        schedule: EventSchedule,
        availability: SessionAvailabilityReader,
    ) -> None:
        self._events = events
        self._schedule = schedule
        self._availability = availability

    def list_for_event(self, event_id: int, viewer: UserAccount | None) -> list[SessionView]:
        """Sessions of a visible event; a hidden or unknown event raises not found."""
        self._events.get(event_id, viewer)
        return self.with_availability(event_id, self._schedule.list_for_event(event_id), viewer)

    def with_availability(
        self,
        event_id: int,
        sessions: Sequence[SessionWithSpeaker],
        viewer: UserAccount | None,
    ) -> list[SessionView]:
        """Seats left and viewer enrollment per session, read live on every call.

        It must never come from a shared cached payload: the viewer changes between calls.
        """
        counts = self._availability.counts_for_event(event_id)
        mine = (
            self._availability.enrolled_session_ids(viewer.id, event_id)
            if viewer is not None and viewer.id is not None
            else set()
        )
        views: list[SessionView] = []
        for item in sessions:
            session_id = item.session.id
            assert session_id is not None
            enrolled = counts.get(session_id, 0)
            views.append(
                SessionView(
                    item,
                    SessionAvailability(
                        enrolled_count=enrolled,
                        available_spots=available_spots(item.session.capacity, enrolled),
                        is_enrolled=session_id in mine,
                    ),
                )
            )
        return views
