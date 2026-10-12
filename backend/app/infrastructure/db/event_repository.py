from datetime import datetime

from sqlalchemy import func, or_
from sqlmodel import Session, col, delete, select

from app.domain.enums import EventStatus
from app.domain.event import Event, EventFilters, ensure_utc
from app.infrastructure.db.like import LIKE_ESCAPE, escape_like
from app.infrastructure.db.mappers import apply_fields, event_to_domain, event_to_fields
from app.infrastructure.db.models import Event as EventRow


class SqlEventRepository:
    """SQLModel implementation of the EventRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: Event) -> Event:
        row = EventRow(organizer_id=event.organizer_id, **event_to_fields(event))
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
        apply_fields(row, event_to_fields(event))
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return event_to_domain(row)

    def list_published_ended_before(self, moment: datetime) -> list[Event]:
        rows = self._session.exec(
            select(EventRow)
            .where(
                col(EventRow.status) == EventStatus.PUBLISHED,
                col(EventRow.end_at) < ensure_utc(moment),
            )
            .order_by(col(EventRow.end_at), col(EventRow.id))
            .with_for_update()
        ).all()
        return [event_to_domain(row) for row in rows]

    def delete(self, event_id: int) -> None:
        # Sessions and registrations go with the event through ON DELETE CASCADE.
        # sqlmodel types exec() for selects only; a Delete runs through the same path.
        self._session.exec(delete(EventRow).where(col(EventRow.id) == event_id))  # type: ignore[call-overload]
