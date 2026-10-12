from collections.abc import Iterator
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.application.errors import SessionNotFoundError
from app.application.ports import EnrollmentRule
from app.domain.event import ensure_utc
from app.domain.session_registration import (
    AlreadyEnrolledError,
    EnrollmentContext,
    SessionParticipantFilters,
    SessionParticipantRow,
    SessionRegistration,
)
from app.infrastructure.db.like import LIKE_ESCAPE, escape_like
from app.infrastructure.db.mappers import (
    event_to_domain,
    session_registration_to_domain,
    session_to_domain,
)
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import SessionRegistration as SessionRegistrationRow
from app.infrastructure.db.models import User as UserRow

ALREADY_ENROLLED = "You are already enrolled in this session"
PARTICIPANT_CHUNK_SIZE = 500


def _participant_conditions(filters: SessionParticipantFilters) -> list[Any]:
    conditions: list[Any] = []
    if filters.organizer_id is not None:
        conditions.append(col(EventRow.organizer_id) == filters.organizer_id)
    if filters.event_id is not None:
        conditions.append(col(EventRow.id) == filters.event_id)
    if filters.session_id is not None:
        conditions.append(col(SessionRow.id) == filters.session_id)
    if filters.status is not None:
        conditions.append(col(EventRow.status) == filters.status)
    if filters.q:
        pattern = f"%{escape_like(filters.q)}%"
        conditions.append(
            or_(
                col(SessionRow.title).ilike(pattern, escape=LIKE_ESCAPE),
                col(EventRow.name).ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if filters.date_from is not None:
        conditions.append(col(SessionRow.start_at) >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(col(SessionRow.start_at) <= filters.date_to)
    return conditions


def _participant_rows(filters: SessionParticipantFilters) -> Any:
    return (
        # sqlmodel's select() is typed up to four columns only.
        select(  # type: ignore[call-overload]
            col(UserRow.full_name),
            col(UserRow.email),
            col(EventRow.name),
            col(SessionRow.title),
            col(SessionRow.start_at),
        )
        .select_from(SessionRegistrationRow)
        .join(SessionRow, col(SessionRow.id) == col(SessionRegistrationRow.session_id))
        .join(EventRow, col(EventRow.id) == col(SessionRow.event_id))
        .join(UserRow, col(UserRow.id) == col(SessionRegistrationRow.user_id))
        .where(*_participant_conditions(filters))
        .order_by(
            col(SessionRow.start_at),
            col(SessionRow.id),
            col(SessionRegistrationRow.created_at),
            col(SessionRegistrationRow.id),
        )
    )


def _to_row(row: Any) -> SessionParticipantRow:
    full_name, email, event_name, session_title, session_start = row
    return SessionParticipantRow(
        full_name, email, event_name, session_title, ensure_utc(session_start)
    )


class SqlSessionRegistrationRepository:
    """SQLModel adapter for the session enrollment ports.

    Implements SessionEnrollmentWriter, SessionAvailabilityReader, SessionParticipantQueries
    and SessionEnrollmentLock over the same table; services depend on each port separately.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def enroll(self, user_id: int, session_id: int, rule: EnrollmentRule) -> SessionRegistration:
        # FOR UPDATE on the session row serializes concurrent enrollments to it; the lock lasts
        # until the unit of work commits, so the last seat is never oversold. Locking the
        # user's event registration too keeps a concurrent event cancellation from leaving an
        # orphan enrollment behind.
        session_row = self._session.exec(
            select(SessionRow).where(col(SessionRow.id) == session_id).with_for_update()
        ).first()
        if session_row is None:
            raise SessionNotFoundError(session_id)
        event_row = self._session.get(EventRow, session_row.event_id)
        assert event_row is not None
        if self.is_enrolled(user_id, session_id):
            raise AlreadyEnrolledError(ALREADY_ENROLLED)
        event_registered = (
            self._session.exec(
                select(RegistrationRow.id)
                .where(
                    col(RegistrationRow.user_id) == user_id,
                    col(RegistrationRow.event_id) == session_row.event_id,
                )
                .with_for_update()
            ).first()
            is not None
        )
        enrolled_count = self._session.exec(
            select(func.count())
            .select_from(SessionRegistrationRow)
            .where(col(SessionRegistrationRow.session_id) == session_id)
        ).one()
        enrolled_rows = self._session.exec(
            select(SessionRow)
            .join(
                SessionRegistrationRow,
                col(SessionRegistrationRow.session_id) == col(SessionRow.id),
            )
            .where(col(SessionRegistrationRow.user_id) == user_id)
        ).all()
        rule(
            EnrollmentContext(
                event=event_to_domain(event_row),
                session=session_to_domain(session_row),
                event_registered=event_registered,
                enrolled_sessions=[session_to_domain(row) for row in enrolled_rows],
                enrolled_count=enrolled_count,
            )
        )
        row = SessionRegistrationRow(user_id=user_id, session_id=session_id)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise AlreadyEnrolledError(ALREADY_ENROLLED) from exc
        self._session.refresh(row)
        return session_registration_to_domain(row)

    def lock_and_count_enrollments(self, session_id: int) -> int:
        # Same FOR UPDATE row lock that enrollment takes, so an enroll cannot slip in
        # between this check and the update or delete that follows in the same transaction.
        self._session.exec(
            select(col(SessionRow.id)).where(col(SessionRow.id) == session_id).with_for_update()
        ).first()
        return self._session.exec(
            select(func.count())
            .select_from(SessionRegistrationRow)
            .where(col(SessionRegistrationRow.session_id) == session_id)
        ).one()

    def is_enrolled(self, user_id: int, session_id: int) -> bool:
        return (
            self._session.exec(
                select(SessionRegistrationRow.id).where(
                    col(SessionRegistrationRow.user_id) == user_id,
                    col(SessionRegistrationRow.session_id) == session_id,
                )
            ).first()
            is not None
        )

    def cancel(self, user_id: int, session_id: int) -> bool:
        # sqlmodel types exec() for selects only; a Delete runs through the same path.
        result = self._session.exec(  # type: ignore[call-overload]
            delete(SessionRegistrationRow).where(
                col(SessionRegistrationRow.user_id) == user_id,
                col(SessionRegistrationRow.session_id) == session_id,
            )
        )
        return bool(result.rowcount > 0)

    def cancel_for_event(self, user_id: int, event_id: int) -> int:
        event_sessions = select(col(SessionRow.id)).where(col(SessionRow.event_id) == event_id)
        result = self._session.exec(  # type: ignore[call-overload]
            delete(SessionRegistrationRow).where(
                col(SessionRegistrationRow.user_id) == user_id,
                col(SessionRegistrationRow.session_id).in_(event_sessions),
            )
        )
        return int(result.rowcount)

    def counts_for_event(self, event_id: int) -> dict[int, int]:
        rows = self._session.exec(
            select(col(SessionRegistrationRow.session_id), func.count())
            .join(SessionRow, col(SessionRow.id) == col(SessionRegistrationRow.session_id))
            .where(col(SessionRow.event_id) == event_id)
            .group_by(col(SessionRegistrationRow.session_id))
        ).all()
        return {session_id: count for session_id, count in rows}

    def enrolled_session_ids(self, user_id: int, event_id: int) -> set[int]:
        rows = self._session.exec(
            select(col(SessionRegistrationRow.session_id))
            .join(SessionRow, col(SessionRow.id) == col(SessionRegistrationRow.session_id))
            .where(
                col(SessionRegistrationRow.user_id) == user_id,
                col(SessionRow.event_id) == event_id,
            )
        ).all()
        return set(rows)

    def list_participants(
        self, filters: SessionParticipantFilters, page: int, size: int
    ) -> tuple[list[SessionParticipantRow], int]:
        total = self._session.exec(
            select(func.count())
            .select_from(SessionRegistrationRow)
            .join(SessionRow, col(SessionRow.id) == col(SessionRegistrationRow.session_id))
            .join(EventRow, col(EventRow.id) == col(SessionRow.event_id))
            .where(*_participant_conditions(filters))
        ).one()
        rows = self._session.exec(
            _participant_rows(filters).offset((page - 1) * size).limit(size)
        ).all()
        return [_to_row(row) for row in rows], total

    def iter_participants(
        self, filters: SessionParticipantFilters
    ) -> Iterator[SessionParticipantRow]:
        # A streamed response outlives the request-scoped session, so the stream reads through
        # its own short-lived one; rows arrive in chunks and memory stays constant.
        with Session(self._session.get_bind()) as session:
            result = session.exec(
                _participant_rows(filters).execution_options(yield_per=PARTICIPANT_CHUNK_SIZE)
            )
            for row in result:
                yield _to_row(row)
