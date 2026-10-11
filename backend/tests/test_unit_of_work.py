import pytest
from sqlmodel import Session, func, select

from app.application.errors import EmailAlreadyRegisteredError, SpeakerEmailTakenError
from app.domain.enums import Role
from app.domain.speaker import Speaker
from app.domain.user import UserAccount
from app.infrastructure.db.models import Speaker as SpeakerRow
from app.infrastructure.db.models import User
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.user_repository import SqlUserRepository


def stored_users(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User)).one()


def test_repository_write_is_visible_to_other_connections_only_after_commit(
    session: Session,
) -> None:
    SqlUserRepository(session).add(
        UserAccount(email="a@x.com", password_hash="h", role=Role.ATTENDEE)
    )
    with Session(session.get_bind()) as other:
        assert stored_users(other) == 0
    SqlUnitOfWork(session).commit()
    with Session(session.get_bind()) as other:
        assert stored_users(other) == 1


def test_rollback_discards_every_flushed_write(session: Session) -> None:
    users = SqlUserRepository(session)
    speakers = SqlSpeakerRepository(session)
    users.add(UserAccount(email="a@x.com", password_hash="h", role=Role.ATTENDEE))
    speakers.add(Speaker(name="Ada", bio="", email=None))

    SqlUnitOfWork(session).rollback()

    assert stored_users(session) == 0
    assert session.exec(select(func.count()).select_from(SpeakerRow)).one() == 0


def test_duplicate_email_is_translated_at_flush_time(session: Session) -> None:
    users = SqlUserRepository(session)
    uow = SqlUnitOfWork(session)
    users.add(UserAccount(email="a@x.com", password_hash="h", role=Role.ATTENDEE))
    uow.commit()

    with pytest.raises(EmailAlreadyRegisteredError):
        users.add(UserAccount(email="a@x.com", password_hash="h", role=Role.ATTENDEE))

    assert (
        users.add(UserAccount(email="b@x.com", password_hash="h", role=Role.ATTENDEE)).id
        is not None
    )


def test_failed_flush_discards_earlier_uncommitted_writes_of_the_same_unit(
    session: Session,
) -> None:
    speakers = SqlSpeakerRepository(session)
    speakers.add(Speaker(name="Ada", bio="", email="a@x.com"))
    SqlUnitOfWork(session).commit()
    speakers.add(Speaker(name="Grace", bio="", email="g@x.com"))

    with pytest.raises(SpeakerEmailTakenError):
        speakers.add(Speaker(name="Dup", bio="", email="a@x.com"))

    assert [s.name for s in speakers.list_page(None, 1, 10)[0]] == ["Ada"]
