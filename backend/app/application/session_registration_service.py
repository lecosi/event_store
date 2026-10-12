"""Session enrollment use cases. Depend only on ports and pure domain rules."""

from app.application.clock import Clock, utc_now
from app.application.errors import DuplicateEntryError
from app.application.guards import EventAccessPolicy, get_event, get_session_in_event
from app.application.ports import (
    EventRepository,
    SessionEnrollmentWriter,
    SessionRepository,
    UnitOfWork,
    transaction,
)
from app.domain.session_registration import (
    ALREADY_ENROLLED,
    AlreadyEnrolledError,
    EnrollmentContext,
    NotEnrolledError,
    SessionRegistration,
    ensure_can_cancel_enrollment,
    ensure_can_enroll,
)
from app.domain.user import UserAccount


class SessionRegistrationService:
    def __init__(
        self,
        events: EventRepository,
        sessions: SessionRepository,
        enrollments: SessionEnrollmentWriter,
        uow: UnitOfWork,
        clock: Clock = utc_now,
    ) -> None:
        self._events = events
        self._access = EventAccessPolicy(events)
        self._sessions = sessions
        self._enrollments = enrollments
        self._uow = uow
        self._clock = clock

    def enroll(self, user: UserAccount, event_id: int, session_id: int) -> SessionRegistration:
        assert user.id is not None
        with transaction(self._uow):
            event = self._access.get_visible(user, event_id)
            get_session_in_event(self._sessions, event_id, session_id)
            session = self._enrollments.lock_session(session_id)
            if self._enrollments.is_enrolled(user.id, session_id):
                raise AlreadyEnrolledError(ALREADY_ENROLLED)
            context = EnrollmentContext(
                event=event,
                session=session,
                event_registered=self._enrollments.lock_event_registration(user.id, event_id),
                enrolled_count=self._enrollments.count_enrollments(session_id),
                enrolled_sessions=self._enrollments.find_overlapping_sessions(user.id, session),
            )
            ensure_can_enroll(context, self._clock())
            try:
                return self._enrollments.add(user.id, session_id)
            except DuplicateEntryError as exc:
                raise AlreadyEnrolledError(ALREADY_ENROLLED) from exc

    def cancel(self, user: UserAccount, event_id: int, session_id: int) -> None:
        assert user.id is not None
        with transaction(self._uow):
            event = get_event(self._events, event_id)
            get_session_in_event(self._sessions, event_id, session_id)
            if not self._enrollments.is_enrolled(user.id, session_id):
                raise NotEnrolledError
            ensure_can_cancel_enrollment(event)
            self._enrollments.cancel(user.id, session_id)
