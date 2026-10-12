from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.domain.enums import EventStatus, Role
from app.domain.session_registration import SessionParticipantFilters, SessionParticipantRow
from app.infrastructure.db import session_registration_repository
from app.infrastructure.db.models import Event, SessionRegistration, Speaker, User
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.session_registration_repository import SqlSessionRegistrationRepository

START = datetime(2030, 3, 10, 9, tzinfo=UTC)


def add_user(session: Session, n: int, role: Role = Role.ATTENDEE) -> User:
    user = User(email=f"u{n}@example.com", full_name=f"User {n}", password_hash="h", role=role)
    session.add(user)
    session.commit()
    return user


def add_event(
    session: Session,
    owner: User,
    name: str,
    status: EventStatus = EventStatus.PUBLISHED,
) -> Event:
    assert owner.id is not None
    event = Event(
        name=name,
        description="",
        location="Lima",
        start_at=START,
        end_at=START + timedelta(days=10),
        capacity=100,
        status=status,
        organizer_id=owner.id,
    )
    session.add(event)
    session.commit()
    return event


def add_speaker(session: Session) -> Speaker:
    speaker = Speaker(name="Ada", bio="", email=None)
    session.add(speaker)
    session.commit()
    return speaker


def add_session(session: Session, event: Event, title: str, days: int = 0) -> SessionRow:
    assert event.id is not None
    speaker = add_speaker(session)
    assert speaker.id is not None
    row = SessionRow(
        event_id=event.id,
        speaker_id=speaker.id,
        title=title,
        start_at=START + timedelta(days=days),
        end_at=START + timedelta(days=days, hours=1),
        capacity=100,
    )
    session.add(row)
    session.commit()
    return row


def enroll(session: Session, user: User, target: SessionRow, minutes: int = 0) -> None:
    assert user.id is not None and target.id is not None
    session.add(
        SessionRegistration(
            user_id=user.id,
            session_id=target.id,
            created_at=START - timedelta(days=1) + timedelta(minutes=minutes),
        )
    )
    session.commit()


@pytest.fixture
def repository(session: Session) -> SqlSessionRegistrationRepository:
    return SqlSessionRegistrationRepository(session)


def test_row_joins_user_event_and_session(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    target = add_session(session, add_event(session, owner, "PyCon"), "Keynote", days=2)
    enroll(session, add_user(session, 1), target)

    rows, total = repository.list_participants(SessionParticipantFilters(), 1, 10)

    assert rows == [
        SessionParticipantRow(
            "User 1", "u1@example.com", "PyCon", "Keynote", START + timedelta(days=2)
        )
    ]
    assert total == 1


def test_streaming_reads_every_row_across_several_chunks(
    session: Session,
    repository: SqlSessionRegistrationRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_registration_repository, "PARTICIPANT_CHUNK_SIZE", 2)
    owner = add_user(session, 0, Role.ORGANIZER)
    target = add_session(session, add_event(session, owner, "PyCon"), "Keynote")
    for n in range(1, 6):
        enroll(session, add_user(session, n), target, minutes=n)

    rows = list(repository.iter_participants(SessionParticipantFilters()))

    assert [row.full_name for row in rows] == [f"User {n}" for n in range(1, 6)]


def test_page_and_stream_share_filters_and_order(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    other = add_user(session, 1, Role.ORGANIZER)
    mine = add_session(session, add_event(session, owner, "Mine"), "Keynote", days=2)
    theirs = add_session(session, add_event(session, other, "Theirs"), "Keynote", days=1)
    for n in range(2, 5):
        enroll(session, add_user(session, n), mine, minutes=n)
        enroll(session, add_user(session, n + 10), theirs, minutes=n)
    filters = SessionParticipantFilters(organizer_id=owner.id)

    page, total = repository.list_participants(filters, 1, 2)
    streamed = list(repository.iter_participants(filters))

    assert total == 3
    assert [row.full_name for row in streamed] == ["User 2", "User 3", "User 4"]
    assert page == streamed[:2]


def test_rows_are_ordered_by_session_start_first(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    event = add_event(session, owner, "PyCon")
    later = add_session(session, event, "Later", days=5)
    sooner = add_session(session, event, "Sooner", days=1)
    enroll(session, add_user(session, 1), later)
    enroll(session, add_user(session, 2), sooner)

    rows, _ = repository.list_participants(SessionParticipantFilters(), 1, 10)

    assert [row.session_title for row in rows] == ["Sooner", "Later"]


def test_event_and_session_filters_narrow_the_rows(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    first_event = add_event(session, owner, "First")
    second_event = add_event(session, owner, "Second")
    keynote = add_session(session, first_event, "Keynote", days=1)
    workshop = add_session(session, first_event, "Workshop", days=2)
    closing = add_session(session, second_event, "Closing", days=3)
    for n, target in enumerate((keynote, workshop, closing), start=1):
        enroll(session, add_user(session, n), target)

    by_event, _ = repository.list_participants(
        SessionParticipantFilters(event_id=first_event.id), 1, 10
    )
    by_session, _ = repository.list_participants(
        SessionParticipantFilters(session_id=closing.id), 1, 10
    )

    assert [row.session_title for row in by_event] == ["Keynote", "Workshop"]
    assert [row.session_title for row in by_session] == ["Closing"]


def test_text_filter_matches_title_or_event_name_with_literal_wildcards(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    pycon = add_event(session, owner, "PyCon")
    other = add_event(session, owner, "Other")
    by_event = add_session(session, pycon, "Keynote", days=1)
    by_title = add_session(session, other, "100% Python", days=2)
    unrelated = add_session(session, other, "100 Python", days=3)
    for n, target in enumerate((by_event, by_title, unrelated), start=1):
        enroll(session, add_user(session, n), target)

    event_match, _ = repository.list_participants(SessionParticipantFilters(q="pycon"), 1, 10)
    wildcard, _ = repository.list_participants(SessionParticipantFilters(q="%"), 1, 10)

    assert [row.session_title for row in event_match] == ["Keynote"]
    assert [row.session_title for row in wildcard] == ["100% Python"]


def test_status_and_date_filters_apply_to_event_status_and_session_start(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    live = add_event(session, owner, "Live")
    draft = add_event(session, owner, "Draft", EventStatus.DRAFT)
    early = add_session(session, live, "Early", days=1)
    late = add_session(session, live, "Late", days=6)
    hidden = add_session(session, draft, "Hidden", days=1)
    for n, target in enumerate((early, late, hidden), start=1):
        enroll(session, add_user(session, n), target)

    published, _ = repository.list_participants(
        SessionParticipantFilters(status=EventStatus.PUBLISHED), 1, 10
    )
    window, _ = repository.list_participants(
        SessionParticipantFilters(
            date_from=START + timedelta(days=5), date_to=START + timedelta(days=7)
        ),
        1,
        10,
    )

    assert [row.session_title for row in published] == ["Early", "Late"]
    assert [row.session_title for row in window] == ["Late"]


def test_event_registration_without_enrollment_does_not_appear(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    owner = add_user(session, 0, Role.ORGANIZER)
    add_session(session, add_event(session, owner, "PyCon"), "Keynote")

    rows, total = repository.list_participants(SessionParticipantFilters(), 1, 10)

    assert (rows, total) == ([], 0)
