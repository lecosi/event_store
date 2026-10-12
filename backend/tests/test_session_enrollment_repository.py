from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.domain.enums import EventStatus, Role
from app.infrastructure.db.mappers import session_to_domain
from app.infrastructure.db.models import Event, SessionRegistration, Speaker, User
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.session_registration_repository import SqlSessionRegistrationRepository
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository

START = datetime(2030, 3, 10, 9, tzinfo=UTC)


def add_user(session: Session, n: int) -> User:
    user = User(
        email=f"u{n}@example.com", full_name=f"User {n}", password_hash="h", role=Role.ATTENDEE
    )
    session.add(user)
    session.commit()
    return user


def add_event(session: Session, owner: User) -> Event:
    assert owner.id is not None
    event = Event(
        name="Conf",
        description="",
        location="Lima",
        start_at=START,
        end_at=START + timedelta(days=10),
        capacity=100,
        status=EventStatus.PUBLISHED,
        organizer_id=owner.id,
    )
    session.add(event)
    session.commit()
    return event


def add_speaker(session: Session, name: str = "Ada") -> Speaker:
    speaker = Speaker(name=name, bio="", email=None)
    session.add(speaker)
    session.commit()
    return speaker


def add_session(session: Session, event: Event, speaker: Speaker, minutes: int) -> SessionRow:
    assert event.id is not None and speaker.id is not None
    row = SessionRow(
        event_id=event.id,
        speaker_id=speaker.id,
        title=f"Talk at {minutes}",
        start_at=START + timedelta(minutes=minutes),
        end_at=START + timedelta(minutes=minutes + 60),
        capacity=100,
    )
    session.add(row)
    session.commit()
    return row


def enroll(session: Session, user: User, target: SessionRow) -> None:
    assert user.id is not None and target.id is not None
    session.add(SessionRegistration(user_id=user.id, session_id=target.id))
    session.commit()


@pytest.fixture
def repository(session: Session) -> SqlSessionRegistrationRepository:
    return SqlSessionRegistrationRepository(session)


def test_overlapping_enrollment_of_the_user_is_returned(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    user = add_user(session, 1)
    event = add_event(session, user)
    speaker = add_speaker(session)
    held = add_session(session, event, speaker, 30)
    enroll(session, user, held)
    target = session_to_domain(add_session(session, event, add_speaker(session, "Bo"), 0))
    assert user.id is not None

    found = repository.find_overlapping_sessions(user.id, target)

    assert [s.id for s in found] == [held.id]


def test_sessions_that_only_touch_do_not_overlap(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    user = add_user(session, 1)
    event = add_event(session, user)
    before = add_session(session, event, add_speaker(session), -60)
    after = add_session(session, event, add_speaker(session, "Bo"), 60)
    enroll(session, user, before)
    enroll(session, user, after)
    target = session_to_domain(add_session(session, event, add_speaker(session, "Cy"), 0))
    assert user.id is not None

    assert repository.find_overlapping_sessions(user.id, target) == []


def test_other_users_enrollments_and_the_session_itself_are_ignored(
    session: Session, repository: SqlSessionRegistrationRepository
) -> None:
    me = add_user(session, 1)
    other = add_user(session, 2)
    event = add_event(session, me)
    theirs = add_session(session, event, add_speaker(session), 10)
    mine = add_session(session, event, add_speaker(session, "Bo"), 0)
    enroll(session, other, theirs)
    enroll(session, me, mine)
    assert me.id is not None

    assert repository.find_overlapping_sessions(me.id, session_to_domain(mine)) == []


def test_get_many_speakers_returns_existing_ones_by_id_and_skips_missing(
    session: Session,
) -> None:
    repo = SqlSpeakerRepository(session)
    ada = add_speaker(session, "Ada")
    grace = add_speaker(session, "Grace")
    assert ada.id is not None and grace.id is not None

    found = repo.get_many({ada.id, grace.id, 9999})

    assert {i: s.name for i, s in found.items()} == {ada.id: "Ada", grace.id: "Grace"}
    assert repo.get_many(set()) == {}
