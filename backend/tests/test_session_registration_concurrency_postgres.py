from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.application.session_registration_service import SessionRegistrationService
from app.domain.enums import EventStatus, Role
from app.domain.registration import RegistrationConflictError
from app.domain.user import UserAccount
from app.infrastructure.db import models
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.session_registration_repository import (
    SqlSessionRegistrationRepository,
)
from app.infrastructure.db.session_repository import SqlSessionRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork

THREADS = 12


@pytest.fixture
def seeded(clean_postgres: Engine) -> Iterator[tuple[int, int]]:
    now = datetime.now(UTC)
    with Session(clean_postgres) as session:
        users = [
            models.User(email=f"u{n}@x.com", full_name="Test User", password_hash="h")
            for n in range(THREADS)
        ]
        organizer = models.User(email="org@x.com", full_name="Test User", password_hash="h")
        speaker = models.Speaker(name="Ada")
        session.add_all([*users, organizer, speaker])
        session.commit()
        event = models.Event(
            name="Race",
            location="Lima",
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=2),
            capacity=THREADS,
            status=EventStatus.PUBLISHED,
            organizer_id=organizer.id,
        )
        session.add(event)
        session.commit()
        talk = models.Session(
            event_id=event.id,
            speaker_id=speaker.id,
            title="Final",
            start_at=now + timedelta(days=1, hours=1),
            end_at=now + timedelta(days=1, hours=2),
            capacity=1,
        )
        session.add(talk)
        session.add_all(models.Registration(user_id=user.id, event_id=event.id) for user in users)
        session.commit()
        yield event.id, talk.id


def test_only_one_enrollment_wins_a_capacity_one_session(
    clean_postgres: Engine, seeded: tuple[int, int]
) -> None:
    event_id, session_id = seeded
    with Session(clean_postgres) as session:
        user_ids = [u.id for u in session.exec(select(models.User)).all() if u.id]

    def attempt(user_id: int) -> bool:
        with Session(clean_postgres) as session:
            enrollments = SqlSessionRegistrationRepository(session)
            service = SessionRegistrationService(
                SqlEventRepository(session),
                SqlSessionRepository(session),
                enrollments,
                enrollments,
                SqlUnitOfWork(session),
            )
            user = UserAccount(
                id=user_id,
                email=f"u{user_id}@x.com",
                full_name="Test User",
                password_hash="h",
                role=Role.ATTENDEE,
            )
            try:
                service.enroll(user, event_id, session_id)
            except RegistrationConflictError:
                return False
            return True

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        results = list(pool.map(attempt, user_ids))

    assert results.count(True) == 1
    with Session(clean_postgres) as session:
        assert len(session.exec(select(models.SessionRegistration)).all()) == 1
