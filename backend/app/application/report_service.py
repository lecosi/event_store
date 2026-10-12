"""Report use cases. Depend only on ports and pure domain rules."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from app.application.errors import PermissionDeniedError, SessionNotFoundError
from app.application.event_service import ORGANIZING_ROLES, EventService
from app.application.ports import (
    RegistrationRepository,
    SessionParticipantQueries,
    SessionRepository,
)
from app.domain.enums import EventStatus, Role
from app.domain.event import EventValidationError, ParticipantFilters
from app.domain.registration import ParticipantPage, ParticipantRow
from app.domain.session_registration import (
    SessionParticipantFilters,
    SessionParticipantPage,
    SessionParticipantRow,
)
from app.domain.user import UserAccount


@dataclass(frozen=True)
class ParticipantParams:
    """Filters requested by the caller; dates are whole UTC days, both inclusive."""

    event_id: int | None = None
    q: str | None = None
    status: EventStatus | None = None
    date_from: date | None = None
    date_to: date | None = None


class ReportService:
    def __init__(self, events: EventService, registrations: RegistrationRepository) -> None:
        self._events = events
        self._registrations = registrations

    def participants(
        self, actor: UserAccount, params: ParticipantParams, page: int, size: int
    ) -> ParticipantPage:
        filters = self._scope(actor, params)
        items, total = self._registrations.list_participants(filters, page, size)
        return ParticipantPage(items=items, total=total, page=page, size=size)

    def iter_participants(
        self, actor: UserAccount, params: ParticipantParams
    ) -> Iterator[ParticipantRow]:
        """Authorize and validate eagerly; the returned iterator only reads rows."""
        return self._registrations.iter_participants(self._scope(actor, params))

    def _scope(self, actor: UserAccount, params: ParticipantParams) -> ParticipantFilters:
        if actor.role not in ORGANIZING_ROLES:
            raise PermissionDeniedError
        if (
            params.date_from is not None
            and params.date_to is not None
            and params.date_to < params.date_from
        ):
            raise EventValidationError("date_to must not be before date_from")
        if params.event_id is not None:
            self._events.ensure_can_manage(actor, params.event_id)
        q = params.q.strip() if params.q else ""
        return ParticipantFilters(
            organizer_id=None if actor.role is Role.ADMIN else actor.id,
            event_id=params.event_id,
            q=q or None,
            status=params.status,
            date_from=_start_of_day(params.date_from),
            date_to=_end_of_day(params.date_to),
        )


@dataclass(frozen=True)
class SessionParticipantParams:
    """Filters requested by the caller; dates are whole UTC days of the session start."""

    event_id: int | None = None
    session_id: int | None = None
    q: str | None = None
    status: EventStatus | None = None
    date_from: date | None = None
    date_to: date | None = None


class SessionReportService:
    def __init__(
        self,
        events: EventService,
        sessions: SessionRepository,
        enrollments: SessionParticipantQueries,
    ) -> None:
        self._events = events
        self._sessions = sessions
        self._enrollments = enrollments

    def participants(
        self, actor: UserAccount, params: SessionParticipantParams, page: int, size: int
    ) -> SessionParticipantPage:
        filters = self._scope(actor, params)
        items, total = self._enrollments.list_participants(filters, page, size)
        return SessionParticipantPage(items=items, total=total, page=page, size=size)

    def iter_participants(
        self, actor: UserAccount, params: SessionParticipantParams
    ) -> Iterator[SessionParticipantRow]:
        """Authorize and validate eagerly; the returned iterator only reads rows."""
        return self._enrollments.iter_participants(self._scope(actor, params))

    def _scope(
        self, actor: UserAccount, params: SessionParticipantParams
    ) -> SessionParticipantFilters:
        if actor.role not in ORGANIZING_ROLES:
            raise PermissionDeniedError
        if (
            params.date_from is not None
            and params.date_to is not None
            and params.date_to < params.date_from
        ):
            raise EventValidationError("date_to must not be before date_from")
        if params.event_id is not None:
            self._events.ensure_can_manage(actor, params.event_id)
        if params.session_id is not None:
            session = self._sessions.get(params.session_id)
            if session is None:
                raise SessionNotFoundError(params.session_id)
            self._events.ensure_can_manage(actor, session.event_id)
        q = params.q.strip() if params.q else ""
        return SessionParticipantFilters(
            organizer_id=None if actor.role is Role.ADMIN else actor.id,
            event_id=params.event_id,
            session_id=params.session_id,
            q=q or None,
            status=params.status,
            date_from=_start_of_day(params.date_from),
            date_to=_end_of_day(params.date_to),
        )


def _start_of_day(day: date | None) -> datetime | None:
    return None if day is None else datetime.combine(day, time.min, tzinfo=UTC)


def _end_of_day(day: date | None) -> datetime | None:
    return None if day is None else datetime.combine(day, time.max, tzinfo=UTC)
