"""Session use cases. Depend only on ports and pure domain rules."""

from app.application.guards import EventAccessPolicy, get_event, get_session_in_event
from app.application.ports import (
    SESSIONS_NAMESPACE,
    Cache,
    EventRepository,
    SessionEnrollmentLock,
    SessionRepository,
    SpeakerRepository,
    UnitOfWork,
    transaction,
)
from app.domain.event import Event
from app.domain.session import (
    Session,
    SessionDetails,
    SessionValidationError,
    SessionWithSpeaker,
    ensure_capacity_covers_enrollments,
    ensure_deletable_without_enrollments,
    ensure_schedule_unchanged,
    ensure_speaker_available,
    ensure_within_event,
    validate_session_capacity,
    validate_session_times,
)
from app.domain.user import UserAccount


class SessionService:
    def __init__(
        self,
        events: EventRepository,
        sessions: SessionRepository,
        speakers: SpeakerRepository,
        enrollment_lock: SessionEnrollmentLock,
        uow: UnitOfWork,
        cache: Cache,
    ) -> None:
        self._events = events
        self._access = EventAccessPolicy(events)
        self._sessions = sessions
        self._speakers = speakers
        self._enrollment_lock = enrollment_lock
        self._uow = uow
        self._cache = cache

    def create(self, actor: UserAccount, event_id: int, details: SessionDetails) -> Session:
        with transaction(self._uow):
            event = self._access.ensure_can_manage_open(actor, event_id)
            session = Session(
                event_id=event_id,
                speaker_id=details.speaker_id,
                title=details.title,
                start_at=details.start_at,
                end_at=details.end_at,
                capacity=details.capacity,
            )
            self._validate(event, session)
            created = self._sessions.add(session)
        self._cache.invalidate(SESSIONS_NAMESPACE)
        return created

    def update(
        self, actor: UserAccount, event_id: int, session_id: int, details: SessionDetails
    ) -> Session:
        with transaction(self._uow):
            event = self._access.ensure_can_manage_open(actor, event_id)
            current = get_session_in_event(self._sessions, event_id, session_id)
            updated = current.with_details(details)
            self._validate(event, updated)
            enrollments = self._enrollment_lock.lock_and_count_enrollments(session_id)
            if enrollments > 0:
                ensure_capacity_covers_enrollments(updated.capacity, enrollments)
                ensure_schedule_unchanged(current, updated)
            saved = self._sessions.update(updated)
        self._cache.invalidate(SESSIONS_NAMESPACE)
        return saved

    def delete(self, actor: UserAccount, event_id: int, session_id: int) -> None:
        with transaction(self._uow):
            self._access.ensure_can_manage_open(actor, event_id)
            get_session_in_event(self._sessions, event_id, session_id)
            ensure_deletable_without_enrollments(
                self._enrollment_lock.lock_and_count_enrollments(session_id)
            )
            self._sessions.delete(session_id)
        self._cache.invalidate(SESSIONS_NAMESPACE)

    def list_for_event(self, event_id: int) -> list[SessionWithSpeaker]:
        get_event(self._events, event_id)
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
