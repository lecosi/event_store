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
from app.infrastructure.db.mappers import event_to_domain, registration_to_domain
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import User as UserRow
from app.infrastructure.db.report_queries import fetch_page, scope_conditions, stream_rows


def _participant_conditions(filters: ParticipantFilters) -> list[Any]:
    return scope_conditions(
        filters,
        date_column=col(EventRow.start_at),
        text_columns=[col(EventRow.name)],
    )


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


def _to_row(row: Any) -> ParticipantRow:
    return ParticipantRow(*row)


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
        count = (
            select(func.count())
            .select_from(RegistrationRow)
            .join(EventRow, col(EventRow.id) == col(RegistrationRow.event_id))
            .where(*_participant_conditions(filters))
        )
        return fetch_page(self._session, _participant_rows(filters), count, _to_row, page, size)

    def iter_participants(self, filters: ParticipantFilters) -> Iterator[ParticipantRow]:
        return stream_rows(self._session, _participant_rows(filters), _to_row)
