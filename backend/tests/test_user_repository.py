import pytest
from sqlmodel import Session

from app.application.errors import EmailAlreadyRegisteredError
from app.domain.user import UserAccount
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.user_repository import SqlUserRepository


def _account(email: str) -> UserAccount:
    return UserAccount(email=email, full_name="Ana Perez", password_hash="hash")


def test_save_persists_name_and_email(session: Session) -> None:
    repo = SqlUserRepository(session)
    user = repo.add(_account("ana@example.com"))
    user.full_name = "Ana Maria"
    user.email = "ana.new@example.com"
    repo.save(user)
    session.commit()
    stored = repo.get_by_id(user.id)
    assert (stored.full_name, stored.email) == ("Ana Maria", "ana.new@example.com")


def test_save_maps_a_unique_violation_to_email_already_registered(session: Session) -> None:
    repo = SqlUserRepository(session)
    repo.add(_account("bob@example.com"))
    ana = repo.add(_account("ana@example.com"))
    session.commit()
    ana.email = "bob@example.com"
    with pytest.raises(EmailAlreadyRegisteredError):
        repo.save(ana)
    SqlUnitOfWork(session).rollback()
    assert repo.get_by_id(ana.id).email == "ana@example.com"
