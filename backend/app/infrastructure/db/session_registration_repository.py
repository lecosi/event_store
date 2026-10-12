from collections.abc import Iterator
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.application.errors import DuplicateEntryError, SessionNotFoundError
from app.domain.event import ensure_utc
from app.domain.session import Session as DomainSession
from app.domain.session_registration import (
    SessionParticipantFilters,
    SessionParticipantRow,
    SessionRegistration,
)
from app.infrastructure.db.mappers import session_registration_to_domain, session_to_domain
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import SessionRegistration as SessionRegistrationRow
from app.infrastructure.db.models import User as UserRow
from app.infrastructure.db.report_queries import fetch_page, scope_conditions, stream_rows


def _participant_conditions(filters: SessionParticipantFilters) -> list[Any]:
    conditions = scope_conditions(
        filters,
        date_column=col(SessionRow.start_at),
        text_columns=[col(SessionRow.title), col(EventRow.name)],
    )
    if filters.session_id is not None:
        conditions.append(col(SessionRow.id) == filters.session_id)
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

    def lock_session(self, session_id: int) -> DomainSession:
        # FOR UPDATE on the session row serializes concurrent enrollments to it; the lock lasts
        # until the unit of work commits, so the last seat is never oversold.
        session_row = self._session.exec(
            select(SessionRow).where(col(SessionRow.id) == session_id).with_for_update()
        ).first()
        if session_row is None:
            raise SessionNotFoundError(session_id)
        return session_to_domain(session_row)

    def lock_event_registration(self, user_id: int, event_id: int) -> bool:
        # Locking the user's event registration keeps a concurrent event cancellation from
        # leaving an orphan enrollment behind.
        return (
            self._session.exec(
                select(RegistrationRow.id)
                .where(
                    col(RegistrationRow.user_id) == user_id,
                    col(RegistrationRow.event_id) == event_id,
                )
                .with_for_update()
            ).first()
            is not None
        )

    def count_enrollments(self, session_id: int) -> int:
        return self._session.exec(
            select(func.count())
            .select_from(SessionRegistrationRow)
            .where(col(SessionRegistrationRow.session_id) == session_id)
        ).one()

    def list_enrolled_sessions(self, user_id: int) -> list[DomainSession]:
        rows = self._session.exec(
            select(SessionRow)
            .join(
                SessionRegistrationRow,
                col(SessionRegistrationRow.session_id) == col(SessionRow.id),
            )
            .where(col(SessionRegistrationRow.user_id) == user_id)
        ).all()
        return [session_to_domain(row) for row in rows]

    def add(self, user_id: int, session_id: int) -> SessionRegistration:
        row = SessionRegistrationRow(user_id=user_id, session_id=session_id)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise DuplicateEntryError from exc
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
        count = (
            select(func.count())
            .select_from(SessionRegistrationRow)
            .join(SessionRow, col(SessionRow.id) == col(SessionRegistrationRow.session_id))
            .join(EventRow, col(EventRow.id) == col(SessionRow.event_id))
            .where(*_participant_conditions(filters))
        )
        return fetch_page(self._session, _participant_rows(filters), count, _to_row, page, size)

    def iter_participants(
        self, filters: SessionParticipantFilters
    ) -> Iterator[SessionParticipantRow]:
        return stream_rows(self._session, _participant_rows(filters), _to_row)
