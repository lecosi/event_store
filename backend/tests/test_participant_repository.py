from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.domain.enums import EventStatus, Role
from app.domain.event import ParticipantFilters
from app.domain.registration import ParticipantRow
from app.infrastructure.db import report_queries
from app.infrastructure.db.models import Event, Registration, User
from app.infrastructure.db.registration_repository import SqlRegistrationRepository

START = datetime(2030, 3, 10, 9, tzinfo=UTC)


def add_user(session: Session, n: int, role: Role = Role.ATTENDEE) -> User:
    user = User(email=f"u{n}@example.com", full_name=f"User {n}", password_hash="h", role=role)
    session.add(user)
    session.commit()
    return user


def add_event(session: Session, owner: User, name: str, days: int = 0) -> Event:
    assert owner.id is not None
    event = Event(
        name=name,
        description="",
        location="Lima",
        start_at=START + timedelta(days=days),
        end_at=START + timedelta(days=days, hours=5),
        capacity=100,
        status=EventStatus.PUBLISHED,
        organizer_id=owner.id,
    )
    session.add(event)
    session.commit()
    return event


def register(session: Session, user: User, event: Event, minutes: int = 0) -> None:
    assert user.id is not None and event.id is not None
    session.add(
        Registration(
            user_id=user.id,
            event_id=event.id,
            created_at=START - timedelta(days=1) + timedelta(minutes=minutes),
        )
    )
    session.commit()


@pytest.fixture
def repository(session: Session) -> SqlRegistrationRepository:
    return SqlRegistrationRepository(session)


def test_streaming_reads_every_row_across_several_chunks(
    session: Session,
    repository: SqlRegistrationRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(report_queries, "PARTICIPANT_CHUNK_SIZE", 2)
    owner = add_user(session, 0, Role.ORGANIZER)
    event = add_event(session, owner, "PyCon")
    for n in range(1, 6):
        register(session, add_user(session, n), event, minutes=n)

    rows = list(repository.iter_participants(ParticipantFilters()))

    assert rows == [ParticipantRow(f"User {n}", f"u{n}@example.com", "PyCon") for n in range(1, 6)]


def test_page_and_stream_share_filters_and_order(
    session: Session, repository: SqlRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    other = add_user(session, 1, Role.ORGANIZER)
    mine = add_event(session, owner, "Mine", days=2)
    theirs = add_event(session, other, "Theirs", days=1)
    for n in range(2, 5):
        register(session, add_user(session, n), mine, minutes=n)
        register(session, add_user(session, n + 10), theirs, minutes=n)
    filters = ParticipantFilters(organizer_id=owner.id)

    page, total = repository.list_participants(filters, 1, 2)
    streamed = list(repository.iter_participants(filters))

    assert total == 3
    assert streamed == [ParticipantRow(f"User {n}", f"u{n}@example.com", "Mine") for n in (2, 3, 4)]
    assert page == streamed[:2]


def test_unfiltered_report_orders_by_event_start_first(
    session: Session, repository: SqlRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    later = add_event(session, owner, "Later", days=5)
    sooner = add_event(session, owner, "Sooner", days=1)
    register(session, add_user(session, 1), later)
    register(session, add_user(session, 2), sooner)

    rows, total = repository.list_participants(ParticipantFilters(), 1, 10)

    assert [row.event_name for row in rows] == ["Sooner", "Later"]
    assert total == 2
