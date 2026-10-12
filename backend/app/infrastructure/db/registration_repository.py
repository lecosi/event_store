from collections.abc import Iterator
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.application.errors import EventNotFoundError
from app.application.ports import RegistrationRule
from app.domain.event import ParticipantFilters, ensure_utc
from app.domain.registration import (
    AlreadyRegisteredError,
    ParticipantRow,
    RegisteredEvent,
    Registration,
)
from app.infrastructure.db.like import LIKE_ESCAPE, escape_like
from app.infrastructure.db.mappers import event_to_domain, registration_to_domain
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import SessionRegistration as SessionRegistrationRow
from app.infrastructure.db.models import User as UserRow

PARTICIPANT_CHUNK_SIZE = 500


def _participant_conditions(filters: ParticipantFilters) -> list[Any]:
    conditions: list[Any] = []
    if filters.organizer_id is not None:
        conditions.append(col(EventRow.organizer_id) == filters.organizer_id)
    if filters.event_id is not None:
        conditions.append(col(EventRow.id) == filters.event_id)
    if filters.status is not None:
        conditions.append(col(EventRow.status) == filters.status)
    if filters.q:
        pattern = f"%{escape_like(filters.q)}%"
        conditions.append(col(EventRow.name).ilike(pattern, escape=LIKE_ESCAPE))
    if filters.date_from is not None:
        conditions.append(col(EventRow.start_at) >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(col(EventRow.start_at) <= filters.date_to)
    return conditions


def _participant_rows(filters: ParticipantFilters) -> Any:
    return (
        select(col(UserRow.full_name), col(UserRow.email), col(EventRow.name))
        .select_from(RegistrationRow)
        .join(EventRow, col(EventRow.id) == col(RegistrationRow.event_id))
        .join(UserRow, col(UserRow.id) == col(RegistrationRow.user_id))
        .where(*_participant_conditions(filters))
        .order_by(
            col(EventRow.start_at),
            col(EventRow.id),
            col(RegistrationRow.created_at),
            col(RegistrationRow.id),
        )
    )


class SqlRegistrationRepository:
    """SQLModel implementation of the RegistrationRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def register(self, user_id: int, event_id: int, rule: RegistrationRule) -> Registration:
        # FOR UPDATE serializes concurrent registrations to the same event. The lock lasts
        # until the unit of work commits, so each one counts the rows committed by the
        # previous one and the last spot is never oversold.
        event_row = self._session.exec(
            select(EventRow).where(col(EventRow.id) == event_id).with_for_update()
        ).first()
        if event_row is None:
            raise EventNotFoundError(event_id)
        if self.is_registered(user_id, event_id):
            raise AlreadyRegisteredError("You are already registered to this event")
        registered = self._session.exec(
            select(func.count())
            .select_from(RegistrationRow)
            .where(col(RegistrationRow.event_id) == event_id)
        ).one()
        rule(event_to_domain(event_row), registered)
        row = RegistrationRow(user_id=user_id, event_id=event_id)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise AlreadyRegisteredError("You are already registered to this event") from exc
        self._session.refresh(row)
        return registration_to_domain(row)

    def is_registered(self, user_id: int, event_id: int) -> bool:
        return (
            self._session.exec(
                select(RegistrationRow.id).where(
                    col(RegistrationRow.user_id) == user_id,
                    col(RegistrationRow.event_id) == event_id,
                )
            ).first()
            is not None
        )

    def cancel(self, user_id: int, event_id: int) -> bool:
        # sqlmodel types exec() for selects only; a Delete runs through the same path.
        result = self._session.exec(  # type: ignore[call-overload]
            delete(RegistrationRow).where(
                col(RegistrationRow.user_id) == user_id,
                col(RegistrationRow.event_id) == event_id,
            )
        )
        # The registration goes first so that it also waits for a concurrent enrollment that
        # holds its row lock; the enrollments deleted afterwards then include that one.
        event_sessions = select(col(SessionRow.id)).where(col(SessionRow.event_id) == event_id)
        self._session.exec(  # type: ignore[call-overload]
            delete(SessionRegistrationRow).where(
                col(SessionRegistrationRow.user_id) == user_id,
                col(SessionRegistrationRow.session_id).in_(event_sessions),
            )
        )
        return bool(result.rowcount > 0)

    def list_for_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[RegisteredEvent], int]:
        mine = col(RegistrationRow.user_id) == user_id
        total = self._session.exec(
            select(func.count()).select_from(RegistrationRow).where(mine)
        ).one()
        rows = self._session.exec(
            select(EventRow, RegistrationRow)
            .join(RegistrationRow, col(RegistrationRow.event_id) == col(EventRow.id))
            .where(mine)
            .order_by(col(EventRow.start_at), col(EventRow.id))
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return [
            RegisteredEvent(event_to_domain(e), ensure_utc(r.created_at)) for e, r in rows
        ], total

    def list_participants(
        self, filters: ParticipantFilters, page: int, size: int
    ) -> tuple[list[ParticipantRow], int]:
        total = self._session.exec(
            select(func.count())
            .select_from(RegistrationRow)
            .join(EventRow, col(EventRow.id) == col(RegistrationRow.event_id))
            .where(*_participant_conditions(filters))
        ).one()
        rows = self._session.exec(
            _participant_rows(filters).offset((page - 1) * size).limit(size)
        ).all()
        return [ParticipantRow(*row) for row in rows], total

    def iter_participants(self, filters: ParticipantFilters) -> Iterator[ParticipantRow]:
        # A streamed response outlives the request-scoped session, so the stream reads through
        # its own short-lived one; rows arrive in chunks and memory stays constant.
        with Session(self._session.get_bind()) as session:
            result = session.exec(
                _participant_rows(filters).execution_options(yield_per=PARTICIPANT_CHUNK_SIZE)
            )
            for row in result:
                yield ParticipantRow(*row)
