import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.application.auth_service import UserAdminService
from app.domain.enums import Role
from app.domain.user import UserAccount
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.user_repository import SqlUserRepository
from tests.fakes import FakeUnitOfWork, FakeUserRepository
from tests.test_auth_api import ADMIN_USERS, make_user, register


def _emails(client: TestClient, headers: dict[str, str], **params: object) -> list[str]:
    response = client.get(ADMIN_USERS, params=params, headers=headers)
    assert response.status_code == 200
    return [item["email"] for item in response.json()["items"]]


@pytest.fixture
def admin(client: TestClient, session: Session) -> dict[str, str]:
    return make_user(client, session, "admin@example.com", Role.ADMIN)


def test_email_filter_matches_prefix_only(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    register(client, "banana@example.com")
    assert _emails(client, admin, email="ana") == ["ana@example.com"]


def test_email_filter_is_case_insensitive(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin, email="ANA@Exa") == ["ana@example.com"]


def test_email_filter_ignores_surrounding_whitespace(
    client: TestClient, admin: dict[str, str]
) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin, email="  ana  ") == ["ana@example.com"]


def test_blank_email_filter_lists_everyone(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin, email="   ") == ["admin@example.com", "ana@example.com"]


def test_missing_email_filter_lists_everyone(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin) == ["admin@example.com", "ana@example.com"]


def test_percent_in_email_filter_is_literal(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin, email="%") == []


def test_underscore_in_email_filter_is_literal(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "a_b@example.com")
    register(client, "axb@example.com")
    assert _emails(client, admin, email="a_") == ["a_b@example.com"]


def test_backslash_in_email_filter_is_literal(client: TestClient, admin: dict[str, str]) -> None:
    register(client, "ana@example.com")
    assert _emails(client, admin, email="\\") == []


def test_pagination_totals_reflect_the_filtered_set(
    client: TestClient, admin: dict[str, str]
) -> None:
    for i in range(5):
        register(client, f"ana{i}@example.com")
    register(client, "bob@example.com")
    body = client.get(
        ADMIN_USERS, params={"email": "ana", "page": 2, "size": 2}, headers=admin
    ).json()
    assert [item["email"] for item in body["items"]] == ["ana2@example.com", "ana3@example.com"]
    assert (body["total"], body["page"], body["size"], body["pages"]) == (5, 2, 2, 3)


def test_email_filter_requires_admin(client: TestClient, session: Session) -> None:
    organizer = make_user(client, session, "org@example.com", Role.ORGANIZER)
    assert client.get(ADMIN_USERS, params={"email": "a"}, headers=organizer).status_code == 403


def test_email_filter_requires_authentication(client: TestClient) -> None:
    assert client.get(ADMIN_USERS, params={"email": "a"}).status_code == 401


def test_repository_matches_prefix_over_mixed_case_stored_emails(session: Session) -> None:
    repo = SqlUserRepository(session)
    repo.add(UserAccount(email="Ana@Example.com", full_name="Ana Perez", password_hash="h"))
    repo.add(UserAccount(email="bob@example.com", full_name="Bob Ray", password_hash="h"))
    SqlUnitOfWork(session).commit()
    users, total = repo.list_page(1, 10, email_prefix="ana@")
    assert ([u.email for u in users], total) == (["Ana@Example.com"], 1)


def test_service_treats_blank_prefix_as_no_filter() -> None:
    repo = FakeUserRepository()
    repo.add(UserAccount(email="ana@example.com", full_name="Ana Perez", password_hash="h"))
    page = UserAdminService(repo, FakeUnitOfWork()).list_users(email_prefix="  ")
    assert page.total == 1


def test_service_strips_the_prefix_before_filtering() -> None:
    repo = FakeUserRepository()
    repo.add(UserAccount(email="ana@example.com", full_name="Ana Perez", password_hash="h"))
    repo.add(UserAccount(email="bob@example.com", full_name="Bob Ray", password_hash="h"))
    page = UserAdminService(repo, FakeUnitOfWork()).list_users(email_prefix=" bo ")
    assert [u.email for u in page.items] == ["bob@example.com"]
