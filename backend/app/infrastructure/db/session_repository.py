from sqlalchemy import func
from sqlmodel import Session, col, select

from app.domain.event import ensure_utc
from app.domain.session import Session as SessionEntity
from app.infrastructure.db.mappers import session_to_domain
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import SessionRegistration as SessionRegistrationRow


def _apply(row: SessionRow, session: SessionEntity) -> None:
    row.speaker_id = session.speaker_id
    row.title = session.title
    row.start_at = ensure_utc(session.start_at)
    row.end_at = ensure_utc(session.end_at)
    row.capacity = session.capacity


class SqlSessionRepository:
    """SQLModel implementation of the SessionRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session: SessionEntity) -> SessionEntity:
        row = SessionRow(
            event_id=session.event_id,
            speaker_id=session.speaker_id,
            title=session.title,
            start_at=ensure_utc(session.start_at),
            end_at=ensure_utc(session.end_at),
            capacity=session.capacity,
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return session_to_domain(row)

    def get(self, session_id: int) -> SessionEntity | None:
        row = self._session.get(SessionRow, session_id)
        return session_to_domain(row) if row else None

    def list_for_event(self, event_id: int) -> list[SessionEntity]:
        rows = self._session.exec(
            select(SessionRow)
            .where(col(SessionRow.event_id) == event_id)
            .order_by(col(SessionRow.start_at), col(SessionRow.id))
        )
        return [session_to_domain(row) for row in rows]

    def list_for_speaker(self, speaker_id: int) -> list[SessionEntity]:
        rows = self._session.exec(
            select(SessionRow).where(col(SessionRow.speaker_id) == speaker_id)
        )
        return [session_to_domain(row) for row in rows]

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

    def update(self, session: SessionEntity) -> SessionEntity:
        row = self._session.get(SessionRow, session.id)
        if row is None:
            raise LookupError(f"Session {session.id} does not exist")
        _apply(row, session)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return session_to_domain(row)

    def delete(self, session_id: int) -> None:
        row = self._session.get(SessionRow, session_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
