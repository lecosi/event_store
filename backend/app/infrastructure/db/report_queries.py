"""Query pieces shared by the participant reports (event registrations and session enrollments)."""

from collections.abc import Callable, Iterator, Sequence
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import or_
from sqlmodel import Session, col

from app.domain.enums import EventStatus
from app.infrastructure.db.like import LIKE_ESCAPE, escape_like
from app.infrastructure.db.models import Event as EventRow

PARTICIPANT_CHUNK_SIZE = 500


class ReportScope(Protocol):
    """The filter fields every participant report shares."""

    @property
    def organizer_id(self) -> int | None: ...

    @property
    def event_id(self) -> int | None: ...

    @property
    def status(self) -> EventStatus | None: ...

    @property
    def q(self) -> str | None: ...

    @property
    def date_from(self) -> datetime | None: ...

    @property
    def date_to(self) -> datetime | None: ...


def scope_conditions(
    scope: ReportScope, *, date_column: Any, text_columns: Sequence[Any]
) -> list[Any]:
    """WHERE conditions for the shared filters.

    ``date_column`` is the column the date range applies to; ``text_columns`` are the columns
    the free-text term is matched against (any of them).
    """
    conditions: list[Any] = []
    if scope.organizer_id is not None:
        conditions.append(col(EventRow.organizer_id) == scope.organizer_id)
    if scope.event_id is not None:
        conditions.append(col(EventRow.id) == scope.event_id)
    if scope.status is not None:
        conditions.append(col(EventRow.status) == scope.status)
    if scope.q:
        pattern = f"%{escape_like(scope.q)}%"
        matches = [column.ilike(pattern, escape=LIKE_ESCAPE) for column in text_columns]
        conditions.append(matches[0] if len(matches) == 1 else or_(*matches))
    if scope.date_from is not None:
        conditions.append(date_column >= scope.date_from)
    if scope.date_to is not None:
        conditions.append(date_column <= scope.date_to)
    return conditions


def fetch_page[T](
    session: Session,
    rows: Any,
    count: Any,
    convert: Callable[[Any], T],
    page: int,
    size: int,
) -> tuple[list[T], int]:
    """Run the count and one page of the ordered row statement."""
    total = session.exec(count).one()
    page_rows = session.exec(rows.offset((page - 1) * size).limit(size)).all()
    return [convert(row) for row in page_rows], total


def stream_rows[T](session: Session, rows: Any, convert: Callable[[Any], T]) -> Iterator[T]:
    """Stream every row of the statement in chunks through its own short-lived session.

    A streamed response outlives the request-scoped session, so the stream reads through a
    new one bound to the same engine; memory stays constant.
    """
    with Session(session.get_bind()) as streaming:
        result = streaming.exec(rows.execution_options(yield_per=PARTICIPANT_CHUNK_SIZE))
        for row in result:
            yield convert(row)
