"""Lookup guards shared by the use cases: visibility, management and nesting checks."""

from app.application.errors import EventNotFoundError, PermissionDeniedError, SessionNotFoundError
from app.application.ports import EventRepository, SessionRepository
from app.domain.enums import Role
from app.domain.event import Event, can_view, ensure_editable
from app.domain.session import Session
from app.domain.user import UserAccount


class EventAccessPolicy:
    """Who may see and who may manage an event; implements the EventAccess port."""

    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def get_visible(self, viewer: UserAccount, event_id: int) -> Event:
        event = self._events.get(event_id)
        # Non-visible events look exactly like missing ones.
        if event is None or not can_view(event, viewer.id, viewer.role is Role.ADMIN):
            raise EventNotFoundError(event_id)
        return event

    def ensure_can_manage(self, actor: UserAccount, event_id: int) -> Event:
        """Return the event when ``actor`` owns it or is an admin; raise otherwise."""
        event = self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        if actor.role is not Role.ADMIN and event.organizer_id != actor.id:
            raise PermissionDeniedError
        return event

    def ensure_can_manage_open(self, actor: UserAccount, event_id: int) -> Event:
        """Like ``ensure_can_manage``, and the event must still be editable."""
        event = self.ensure_can_manage(actor, event_id)
        ensure_editable(event.status)
        return event


def get_event(events: EventRepository, event_id: int) -> Event:
    event = events.get(event_id)
    if event is None:
        raise EventNotFoundError(event_id)
    return event


def get_session_in_event(sessions: SessionRepository, event_id: int, session_id: int) -> Session:
    session = sessions.get(session_id)
    if session is None or session.event_id != event_id:
        raise SessionNotFoundError(session_id)
    return session
