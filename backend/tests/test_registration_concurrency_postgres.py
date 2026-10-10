from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from functools import partial

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, select

from app.domain.enums import EventStatus
from app.domain.registration import RegistrationConflictError, ensure_can_register
from app.infrastructure.db import models
from app.infrastructure.db.registration_repository import SqlRegistrationRepository

THREADS = 12


@pytest.fixture
def seeded(clean_postgres: Engine) -> Iterator[int]:
    now = datetime.now(UTC)
    with Session(clean_postgres) as session:
        users = [models.User(email=f"u{n}@x.com", password_hash="h") for n in range(THREADS)]
        session.add_all(users)
        organizer = models.User(email="org@x.com", password_hash="h")
        session.add(organizer)
        session.commit()
        event = models.Event(
            name="Race",
            location="Lima",
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=2),
            capacity=1,
            status=EventStatus.PUBLISHED,
            organizer_id=organizer.id,
        )
        session.add(event)
        session.commit()
        yield event.id


def test_only_one_registration_wins_a_capacity_one_event(
    clean_postgres: Engine, seeded: int
) -> None:
    with Session(clean_postgres) as session:
        user_ids = [u.id for u in session.exec(select(models.User)).all() if u.id]
    rule = partial(ensure_can_register, now=datetime.now(UTC))

    def attempt(user_id: int) -> bool:
        with Session(clean_postgres) as session:
            try:
                SqlRegistrationRepository(session).register(user_id, seeded, rule)
            except RegistrationConflictError:
                return False
            return True

    with ThreadPoolExecutor(max_workers=THREADS) as pool:
        results = list(pool.map(attempt, user_ids))

    assert results.count(True) == 1
    with Session(clean_postgres) as session:
        assert len(session.exec(select(models.Registration)).all()) == 1
