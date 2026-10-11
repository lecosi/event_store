from datetime import datetime

from sqlalchemy import func, or_
from sqlmodel import Session, col, delete, select

from app.domain.enums import EventStatus
from app.domain.event import Event, EventFilters, ensure_utc
from app.infrastructure.db.like import LIKE_ESCAPE, escape_like
from app.infrastructure.db.mappers import event_to_domain
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration
from app.infrastructure.db.models import Session as SessionRow


def _apply(row: EventRow, event: Event) -> None:
    row.name = event.name
    row.description = event.description
    row.location = event.location
    row.start_at = ensure_utc(event.start_at)
    row.end_at = ensure_utc(event.end_at)
    row.capacity = event.capacity
    row.status = event.status


class SqlEventRepository:
    """SQLModel implementation of the EventRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: Event) -> Event:
        row = EventRow(organizer_id=event.organizer_id, **_fields(event))
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return event_to_domain(row)

    def get(self, event_id: int) -> Event | None:
        row = self._session.get(EventRow, event_id)
        return event_to_domain(row) if row else None

    def list_page(self, filters: EventFilters, page: int, size: int) -> tuple[list[Event], int]:
        conditions = []
        if not filters.unrestricted:
            visible = [col(EventRow.status) == EventStatus.PUBLISHED]
            if filters.viewer_id is not None:
                visible.append(col(EventRow.organizer_id) == filters.viewer_id)
            conditions.append(or_(*visible))
        if filters.status is not None:
            conditions.append(col(EventRow.status) == filters.status)
        if filters.q:
            # Bound parameter + escaped wildcards: never build SQL from user input.
            pattern = f"%{escape_like(filters.q)}%"
            conditions.append(col(EventRow.name).ilike(pattern, escape=LIKE_ESCAPE))

        total = self._session.exec(
            select(func.count()).select_from(EventRow).where(*conditions)
        ).one()
        rows = self._session.exec(
            select(EventRow)
            .where(*conditions)
            .order_by(col(EventRow.start_at), col(EventRow.id))
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return [event_to_domain(row) for row in rows], total

    def update(self, event: Event) -> Event:
        row = self._session.get(EventRow, event.id)
        if row is None:
            raise LookupError(f"Event {event.id} does not exist")
        _apply(row, event)
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return event_to_domain(row)

    def delete(self, event_id: int) -> None:
        # Sessions and registrations go with the event through ON DELETE CASCADE.
        # sqlmodel types exec() for selects only; a Delete runs through the same path.
        self._session.exec(delete(EventRow).where(col(EventRow.id) == event_id))  # type: ignore[call-overload]

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


def _fields(event: Event) -> dict[str, object]:
    return {
        "name": event.name,
        "description": event.description,
        "location": event.location,
        "start_at": ensure_utc(event.start_at),
        "end_at": ensure_utc(event.end_at),
        "capacity": event.capacity,
        "status": event.status,
    }
