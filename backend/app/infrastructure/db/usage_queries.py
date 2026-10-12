from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.domain.event import ensure_utc
from app.infrastructure.db.models import Registration
from app.infrastructure.db.models import Session as SessionRow


class SqlEventUsageQueries:
    """SQLModel implementation of the EventUsageQueries port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_registrations(self, event_id: int) -> int:
        return self._session.exec(
            select(func.count())
            .select_from(Registration)
            .where(col(Registration.event_id) == event_id)
        ).one()

    def max_session_capacity(self, event_id: int) -> int:
        largest = self._session.exec(
            select(func.max(SessionRow.capacity)).where(col(SessionRow.event_id) == event_id)
        ).one()
        return largest or 0

    def session_bounds(self, event_id: int) -> tuple[datetime, datetime] | None:
        first, last = self._session.exec(
            select(func.min(SessionRow.start_at), func.max(SessionRow.end_at)).where(
                col(SessionRow.event_id) == event_id
            )
        ).one()
        if first is None or last is None:
            return None
        return ensure_utc(first), ensure_utc(last)


class SqlSpeakerUsageQueries:
    """SQLModel implementation of the SpeakerUsageQueries port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_sessions(self, speaker_id: int) -> int:
        return self._session.exec(
            select(func.count())
            .select_from(SessionRow)
            .where(col(SessionRow.speaker_id) == speaker_id)
        ).one()
