"""Session use cases. Depend only on ports and pure domain rules."""

from app.application.errors import EventNotFoundError, PermissionDeniedError, SessionNotFoundError
from app.application.ports import EventRepository, SessionRepository, SpeakerRepository
from app.domain.enums import Role
from app.domain.event import Event, ensure_editable
from app.domain.session import (
    Session,
    SessionDetails,
    SessionValidationError,
    SessionWithSpeaker,
    ensure_speaker_available,
    ensure_within_event,
    validate_session_capacity,
    validate_session_times,
)
from app.domain.user import UserAccount


class SessionService:
    def __init__(
        self, events: EventRepository, sessions: SessionRepository, speakers: SpeakerRepository
    ) -> None:
        self._events = events
        self._sessions = sessions
        self._speakers = speakers

    def create(self, actor: UserAccount, event_id: int, details: SessionDetails) -> Session:
        event = self._get_managed_open(actor, event_id)
        session = Session(
            event_id=event_id,
            speaker_id=details.speaker_id,
            title=details.title,
            start_at=details.start_at,
            end_at=details.end_at,
            capacity=details.capacity,
        )
        self._validate(event, session)
        return self._sessions.add(session)

    def update(
        self, actor: UserAccount, event_id: int, session_id: int, details: SessionDetails
    ) -> Session:
        event = self._get_managed_open(actor, event_id)
        updated = self._get_in_event(event_id, session_id).with_details(details)
        self._validate(event, updated)
        return self._sessions.update(updated)

    def delete(self, actor: UserAccount, event_id: int, session_id: int) -> None:
        self._get_managed_open(actor, event_id)
        self._get_in_event(event_id, session_id)
        self._sessions.delete(session_id)

    def list_for_event(self, event_id: int) -> list[SessionWithSpeaker]:
        if self._events.get(event_id) is None:
            raise EventNotFoundError(event_id)
        sessions = self._sessions.list_for_event(event_id)
        names: dict[int, str] = {}
        for session in sessions:
            if session.speaker_id not in names:
                speaker = self._speakers.get(session.speaker_id)
                names[session.speaker_id] = speaker.name if speaker else ""
        return [SessionWithSpeaker(s, names[s.speaker_id]) for s in sessions]

    def get_with_speaker(self, session: Session) -> SessionWithSpeaker:
        speaker = self._speakers.get(session.speaker_id)
        return SessionWithSpeaker(session, speaker.name if speaker else "")

    def _validate(self, event: Event, session: Session) -> None:
        validate_session_times(session.start_at, session.end_at)
        ensure_within_event(session.start_at, session.end_at, event.start_at, event.end_at)
        validate_session_capacity(session.capacity, event.capacity)
        if self._speakers.get(session.speaker_id) is None:
            raise SessionValidationError("speaker does not exist")
        ensure_speaker_available(session, self._sessions.list_for_speaker(session.speaker_id))

    def _get_managed_open(self, actor: UserAccount, event_id: int) -> Event:
        event = self._events.get(event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        if actor.role is not Role.ADMIN and event.organizer_id != actor.id:
            raise PermissionDeniedError
        ensure_editable(event.status)
        return event

    def _get_in_event(self, event_id: int, session_id: int) -> Session:
        session = self._sessions.get(session_id)
        if session is None or session.event_id != event_id:
            raise SessionNotFoundError(session_id)
        return session
