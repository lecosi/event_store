"""Report use cases. Depend only on ports and pure domain rules."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Protocol

from app.application.errors import PermissionDeniedError, SessionNotFoundError
from app.application.ports import (
    EventAccess,
    RegistrationRepository,
    SessionParticipantQueries,
    SessionRepository,
)
from app.domain.enums import EventStatus, Role
from app.domain.event import EventValidationError, ParticipantFilters
from app.domain.registration import ParticipantPage, ParticipantRow
from app.domain.roles import ORGANIZING_ROLES
from app.domain.session_registration import (
    SessionParticipantFilters,
    SessionParticipantPage,
    SessionParticipantRow,
)
from app.domain.user import UserAccount


class _ReportParams(Protocol):
    """The caller filters every participant report accepts."""

    @property
    def event_id(self) -> int | None: ...

    @property
    def q(self) -> str | None: ...

    @property
    def status(self) -> EventStatus | None: ...

    @property
    def date_from(self) -> date | None: ...

    @property
    def date_to(self) -> date | None: ...


@dataclass(frozen=True)
class _ReportScope:
    """Validated, authorized filters resolved from the caller's params."""

    organizer_id: int | None
    event_id: int | None
    q: str | None
    status: EventStatus | None
    date_from: datetime | None
    date_to: datetime | None


def _resolve_scope(access: EventAccess, actor: UserAccount, params: _ReportParams) -> _ReportScope:
    if actor.role not in ORGANIZING_ROLES:
        raise PermissionDeniedError
    if (
        params.date_from is not None
        and params.date_to is not None
        and params.date_to < params.date_from
    ):
        raise EventValidationError("date_to must not be before date_from")
    if params.event_id is not None:
        access.ensure_can_manage(actor, params.event_id)
    q = params.q.strip() if params.q else ""
    return _ReportScope(
        organizer_id=None if actor.role is Role.ADMIN else actor.id,
        event_id=params.event_id,
        q=q or None,
        status=params.status,
        date_from=_start_of_day(params.date_from),
        date_to=_end_of_day(params.date_to),
    )


@dataclass(frozen=True)
class ParticipantParams:
    """Filters requested by the caller; dates are whole UTC days, both inclusive."""

    event_id: int | None = None
    q: str | None = None
    status: EventStatus | None = None
    date_from: date | None = None
    date_to: date | None = None


class ReportService:
    def __init__(self, access: EventAccess, registrations: RegistrationRepository) -> None:
        self._access = access
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
        scope = _resolve_scope(self._access, actor, params)
        return ParticipantFilters(
            organizer_id=scope.organizer_id,
            event_id=scope.event_id,
            q=scope.q,
            status=scope.status,
            date_from=scope.date_from,
            date_to=scope.date_to,
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
        access: EventAccess,
        sessions: SessionRepository,
        enrollments: SessionParticipantQueries,
    ) -> None:
        self._access = access
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
        scope = _resolve_scope(self._access, actor, params)
        if params.session_id is not None:
            session = self._sessions.get(params.session_id)
            if session is None:
                raise SessionNotFoundError(params.session_id)
            self._access.ensure_can_manage(actor, session.event_id)
        return SessionParticipantFilters(
            organizer_id=scope.organizer_id,
            event_id=scope.event_id,
            session_id=params.session_id,
            q=scope.q,
            status=scope.status,
            date_from=scope.date_from,
            date_to=scope.date_to,
        )


def _start_of_day(day: date | None) -> datetime | None:
    return None if day is None else datetime.combine(day, time.min, tzinfo=UTC)


def _end_of_day(day: date | None) -> datetime | None:
    return None if day is None else datetime.combine(day, time.max, tzinfo=UTC)
