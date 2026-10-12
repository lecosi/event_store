from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.application.errors import SessionNotFoundError
from app.application.ports import EnrollmentRule
from app.domain.session_registration import (
    AlreadyEnrolledError,
    EnrollmentContext,
    SessionRegistration,
)
from app.infrastructure.db.mappers import (
    event_to_domain,
    session_registration_to_domain,
    session_to_domain,
)
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import SessionRegistration as SessionRegistrationRow

ALREADY_ENROLLED = "You are already enrolled in this session"


class SqlSessionRegistrationRepository:
    """SQLModel implementation of the SessionRegistrationRepository port."""

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
