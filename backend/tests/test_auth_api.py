import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.domain.enums import Role
from app.infrastructure.db.models import User
from app.infrastructure.security.jwt_tokens import JwtTokenService

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/users/me"


def register(client: TestClient, email: str = "ana@example.com", password: str = "supersecret"):
    return client.post(REGISTER, json={"email": email, "password": password})


def login_headers(client: TestClient, email: str, password: str = "supersecret") -> dict[str, str]:
    token = client.post(LOGIN, json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_user(client: TestClient, session: Session, email: str, role: Role) -> dict[str, str]:
    register(client, email)
    user = session.exec(select(User).where(User.email == email)).one()
    user.role = role
    session.add(user)
    session.commit()
    return login_headers(client, email)


def test_register_ok_hides_password_and_stores_argon2(client: TestClient, session: Session) -> None:
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert body["role"] == "organizer"
    assert "password" not in body and "password_hash" not in body
    stored = session.exec(select(User)).one()
    assert stored.password_hash.startswith("$argon2")


def test_register_ignores_role_sent_by_client(client: TestClient, session: Session) -> None:
    response = client.post(
        REGISTER, json={"email": "eve@example.com", "password": "supersecret", "role": "admin"}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "organizer"
    assert session.exec(select(User)).one().role is Role.ORGANIZER


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    register(client)
    assert register(client).status_code == 409


def test_register_validation(client: TestClient) -> None:
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_login_ok(client: TestClient) -> None:
    register(client)
    response = client.post(LOGIN, json={"email": "ana@example.com", "password": "supersecret"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_failures_are_generic(client: TestClient) -> None:
    register(client)
    bad_pw = client.post(LOGIN, json={"email": "ana@example.com", "password": "wrongpassword"})
    unknown = client.post(LOGIN, json={"email": "nobody@example.com", "password": "supersecret"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()


def test_me_requires_valid_token(client: TestClient) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer junk"}).status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    register(client)
    response = client.get(ME, headers=login_headers(client, "ana@example.com"))
    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"


def test_expired_token_is_unauthorized(client: TestClient, session: Session) -> None:
    register(client)
    user = session.exec(select(User)).one()
    token = JwtTokenService(os.environ["JWT_SECRET"], "HS256", -1).create_access_token(user.id)
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_deactivated_user_loses_access(client: TestClient, session: Session) -> None:
    headers = make_user(client, session, "ana@example.com", Role.ATTENDEE)
    user = session.exec(select(User)).one()
    user.is_active = False
    session.add(user)
    session.commit()
    assert client.get(ME, headers=headers).status_code == 401


@pytest.mark.parametrize("role", [Role.ADMIN, Role.ORGANIZER])
def test_require_role_allows_listed_roles(role: Role) -> None:
    from app.api.dependencies import require_role
    from app.domain.user import UserAccount

    user = UserAccount(email="x@example.com", password_hash="h", role=role, id=1)
    assert require_role(Role.ADMIN, Role.ORGANIZER)(user) is user


def test_require_role_rejects_other_roles() -> None:
    from fastapi import HTTPException

    from app.api.dependencies import require_role
    from app.domain.user import UserAccount

    user = UserAccount(email="x@example.com", password_hash="h", role=Role.ATTENDEE, id=1)
    with pytest.raises(HTTPException) as excinfo:
        require_role(Role.ADMIN)(user)
    assert excinfo.value.status_code == 403
