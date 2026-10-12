"""Session enrollment use cases. Depend only on ports and pure domain rules."""

from collections.abc import Mapping

from app.application.clock import Clock, utc_now
from app.application.errors import DuplicateEntryError
from app.application.guards import EventAccessPolicy, get_event, get_session_in_event
from app.application.ports import (
    EventRepository,
    SessionAvailabilityReader,
    SessionEnrollmentWriter,
    SessionRepository,
    UnitOfWork,
    transaction,
)
from app.domain.registration import available_spots
from app.domain.session_registration import (
    ALREADY_ENROLLED,
    AlreadyEnrolledError,
    EnrollmentContext,
    NotEnrolledError,
    SessionAvailability,
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
        availability: SessionAvailabilityReader,
        uow: UnitOfWork,
        clock: Clock = utc_now,
    ) -> None:
        self._events = events
        self._access = EventAccessPolicy(events)
        self._sessions = sessions
        self._enrollments = enrollments
        self._availability = availability
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
                enrolled_sessions=self._enrollments.list_enrolled_sessions(user.id),
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

    def availability(
        self, event_id: int, capacities: Mapping[int, int], viewer: UserAccount | None
    ) -> dict[int, SessionAvailability]:
        """Seats left and viewer enrollment per session id, given each session's capacity.

        Read live on every call: it must never come from a shared cached payload.
        """
        counts = self._availability.counts_for_event(event_id)
        mine = (
            self._availability.enrolled_session_ids(viewer.id, event_id)
            if viewer is not None and viewer.id is not None
            else set()
        )
        result: dict[int, SessionAvailability] = {}
        for session_id, capacity in capacities.items():
            enrolled = counts.get(session_id, 0)
            result[session_id] = SessionAvailability(
                enrolled_count=enrolled,
                available_spots=available_spots(capacity, enrolled),
                is_enrolled=session_id in mine,
            )
        return result
