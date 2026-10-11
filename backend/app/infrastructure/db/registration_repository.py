from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.application.errors import EventNotFoundError
from app.application.ports import RegistrationRule
from app.domain.event import ensure_utc
from app.domain.registration import AlreadyRegisteredError, RegisteredEvent, Registration
from app.infrastructure.db.mappers import event_to_domain, registration_to_domain
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow


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
