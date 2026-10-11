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
ADMIN_USERS = "/api/v1/admin/users"


def register(
    client: TestClient,
    email: str = "ana@example.com",
    password: str = "supersecret",
    full_name: str = "Ana Perez",
):
    return client.post(
        REGISTER, json={"email": email, "password": password, "full_name": full_name}
    )


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
        REGISTER,
        json={
            "email": "eve@example.com",
            "password": "supersecret",
            "full_name": "Eve Adams",
            "role": "admin",
        },
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


def test_register_returns_the_full_name(client: TestClient) -> None:
    response = register(client, full_name="Ana Perez")
    assert response.status_code == 201
    assert response.json()["full_name"] == "Ana Perez"


def test_register_requires_full_name(client: TestClient) -> None:
    response = client.post(REGISTER, json={"email": "ana@example.com", "password": "supersecret"})
    assert response.status_code == 422


@pytest.mark.parametrize("full_name", ["", "   ", "\t\n"])
def test_register_rejects_blank_full_name(client: TestClient, full_name: str) -> None:
    assert register(client, full_name=full_name).status_code == 422


def test_register_rejects_full_name_longer_than_200_characters(client: TestClient) -> None:
    assert register(client, full_name="a" * 201).status_code == 422


def test_register_accepts_full_name_of_exactly_200_characters(client: TestClient) -> None:
    response = register(client, full_name="a" * 200)
    assert response.status_code == 201
    assert response.json()["full_name"] == "a" * 200


def test_register_trims_surrounding_whitespace_of_full_name(
    client: TestClient, session: Session
) -> None:
    response = register(client, full_name="  Ana Perez  ")
    assert response.json()["full_name"] == "Ana Perez"
    assert session.exec(select(User)).one().full_name == "Ana Perez"


def test_me_returns_the_full_name_after_login(client: TestClient) -> None:
    register(client, full_name="Ana Perez")
    response = client.get(ME, headers=login_headers(client, "ana@example.com"))
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Perez"


def test_admin_users_list_includes_full_names(client: TestClient, session: Session) -> None:
    headers = make_user(client, session, "root@example.com", Role.ADMIN)
    register(client, "ana@example.com", full_name="Ana Perez")
    items = client.get(ADMIN_USERS, headers=headers).json()["items"]
    assert {item["email"]: item["full_name"] for item in items} == {
        "root@example.com": "Ana Perez",
        "ana@example.com": "Ana Perez",
    }


def test_admin_update_response_includes_full_name(client: TestClient, session: Session) -> None:
    headers = make_user(client, session, "root@example.com", Role.ADMIN)
    created = register(client, "ana@example.com", full_name="Ana Perez").json()
    response = client.patch(
        f"{ADMIN_USERS}/{created['id']}", json={"role": "attendee"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Perez"


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

    user = UserAccount(
        email="x@example.com", full_name="Test User", password_hash="h", role=role, id=1
    )
    assert require_role(Role.ADMIN, Role.ORGANIZER)(user) is user


def test_require_role_rejects_other_roles() -> None:
    from fastapi import HTTPException

    from app.api.dependencies import require_role
    from app.domain.user import UserAccount

    user = UserAccount(
        email="x@example.com", full_name="Test User", password_hash="h", role=Role.ATTENDEE, id=1
    )
    with pytest.raises(HTTPException) as excinfo:
        require_role(Role.ADMIN)(user)
    assert excinfo.value.status_code == 403


def test_admin_endpoints_forbidden_for_non_admins(client: TestClient, session: Session) -> None:
    attendee = make_user(client, session, "att@example.com", Role.ATTENDEE)
    organizer = make_user(client, session, "org@example.com", Role.ORGANIZER)
    for headers in (attendee, organizer):
        assert client.get(ADMIN_USERS, headers=headers).status_code == 403
        assert (
            client.patch(f"{ADMIN_USERS}/1", json={"role": "admin"}, headers=headers).status_code
            == 403
        )
    assert client.get(ADMIN_USERS).status_code == 401


def test_admin_lists_and_updates_users(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    listing = client.get(ADMIN_USERS, headers=admin)
    assert listing.status_code == 200
    users = listing.json()["items"]
    assert {u["email"] for u in users} == {"admin@example.com", "ana@example.com"}
    assert all("password_hash" not in u for u in users)

    ana_id = next(u["id"] for u in users if u["email"] == "ana@example.com")
    patched = client.patch(
        f"{ADMIN_USERS}/{ana_id}", json={"role": "organizer", "is_active": False}, headers=admin
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "organizer"
    assert patched.json()["is_active"] is False
    assert (
        client.patch(f"{ADMIN_USERS}/999", json={"role": "admin"}, headers=admin).status_code == 404
    )
    assert (
        client.patch(f"{ADMIN_USERS}/{ana_id}", json={"role": "root"}, headers=admin).status_code
        == 422
    )


def _my_id(client: TestClient, headers: dict[str, str]) -> int:
    return client.get(ME, headers=headers).json()["id"]


def test_admin_cannot_demote_or_deactivate_self(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    me = _my_id(client, admin)
    for body in ({"role": "organizer"}, {"role": "attendee"}, {"is_active": False}):
        response = client.patch(f"{ADMIN_USERS}/{me}", json=body, headers=admin)
        assert response.status_code == 409
        assert response.json() == {"detail": "Admins cannot demote or deactivate their own account"}
    current = client.get(ME, headers=admin).json()
    assert (current["role"], current["is_active"]) == ("admin", True)


def test_admin_self_noop_update_still_succeeds(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    me = _my_id(client, admin)
    response = client.patch(
        f"{ADMIN_USERS}/{me}", json={"role": "admin", "is_active": True}, headers=admin
    )
    assert response.status_code == 200


def test_admin_can_demote_and_deactivate_another_admin(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    second = _my_id(client, make_user(client, session, "second@example.com", Role.ADMIN))
    third = _my_id(client, make_user(client, session, "third@example.com", Role.ADMIN))
    demoted = client.patch(f"{ADMIN_USERS}/{second}", json={"role": "organizer"}, headers=admin)
    assert demoted.status_code == 200 and demoted.json()["role"] == "organizer"
    off = client.patch(f"{ADMIN_USERS}/{third}", json={"is_active": False}, headers=admin)
    assert off.status_code == 200 and off.json()["is_active"] is False


def test_admin_users_pagination(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    for i in range(24):
        register(client, f"user{i:02d}@example.com")

    first = client.get(ADMIN_USERS, params={"page": 1, "size": 10}, headers=admin).json()
    assert (first["total"], first["page"], first["size"], first["pages"]) == (25, 1, 10, 3)
    ids = [u["id"] for u in first["items"]]
    assert ids == sorted(ids) and len(ids) == 10
    last = client.get(ADMIN_USERS, params={"page": 3, "size": 10}, headers=admin).json()
    assert len(last["items"]) == 5
    beyond = client.get(ADMIN_USERS, params={"page": 4, "size": 10}, headers=admin).json()
    assert beyond["items"] == [] and beyond["total"] == 25
    default = client.get(ADMIN_USERS, headers=admin).json()
    assert (default["page"], default["size"], len(default["items"])) == (1, 10, 10)


def test_admin_users_param_validation_and_permissions(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    for params in ({"page": 0}, {"size": 0}, {"size": 101}):
        response = client.get(ADMIN_USERS, params=params, headers=admin)
        assert response.status_code == 422, params
    organizer = make_user(client, session, "org@example.com", Role.ORGANIZER)
    assert client.get(ADMIN_USERS, headers=organizer).status_code == 403


def _user_id(client: TestClient, email: str, headers: dict[str, str]) -> int:
    users = client.get(ADMIN_USERS, headers=headers).json()["items"]
    return next(u["id"] for u in users if u["email"] == email)


def test_admin_changes_only_the_name_of_a_user(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    response = client.patch(
        f"{ADMIN_USERS}/{ana}", json={"full_name": "  Ana Maria  "}, headers=admin
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["full_name"], body["email"], body["role"], body["is_active"]) == (
        "Ana Maria",
        "ana@example.com",
        "organizer",
        True,
    )


def test_admin_changes_only_the_email_of_a_user(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    response = client.patch(
        f"{ADMIN_USERS}/{ana}", json={"email": "ana.new@example.com"}, headers=admin
    )
    assert response.status_code == 200
    assert response.json()["email"] == "ana.new@example.com"
    assert response.json()["full_name"] == "Ana Perez"


def test_admin_changes_name_email_and_role_in_one_request(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    response = client.patch(
        f"{ADMIN_USERS}/{ana}",
        json={"full_name": "Ana M. Perez", "email": "ana.m@example.com", "role": "attendee"},
        headers=admin,
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["full_name"], body["email"], body["role"]) == (
        "Ana M. Perez",
        "ana.m@example.com",
        "attendee",
    )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"full_name": None, "email": None, "role": None, "is_active": None},
        {"full_name": ""},
        {"full_name": "   "},
        {"full_name": "x" * 201},
        {"email": "not-an-email"},
        {"email": ""},
    ],
)
def test_admin_update_rejects_invalid_or_empty_bodies(
    client: TestClient, session: Session, body: dict[str, object]
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    assert client.patch(f"{ADMIN_USERS}/{ana}", json=body, headers=admin).status_code == 422
    current = client.get(ADMIN_USERS, headers=admin).json()["items"]
    assert {u["email"]: u["full_name"] for u in current}["ana@example.com"] == "Ana Perez"


def test_admin_cannot_use_an_email_taken_by_another_user(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    register(client, "bob@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    response = client.patch(
        f"{ADMIN_USERS}/{ana}", json={"email": "bob@example.com"}, headers=admin
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    assert login_headers(client, "ana@example.com")


def test_admin_resending_the_current_email_is_not_a_conflict(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    response = client.patch(
        f"{ADMIN_USERS}/{ana}",
        json={"email": "ana@example.com", "full_name": "Ana Maria"},
        headers=admin,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Maria"


def test_admin_email_is_normalized_and_conflicts_like_registration(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    register(client, "bob@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    taken = client.patch(f"{ADMIN_USERS}/{ana}", json={"email": " BOB@Example.com "}, headers=admin)
    assert taken.status_code == 409
    renamed = client.patch(
        f"{ADMIN_USERS}/{ana}", json={"email": "  Ana.New@Example.COM "}, headers=admin
    )
    assert renamed.status_code == 200
    assert renamed.json()["email"] == "ana.new@example.com"


def test_login_works_with_the_new_email_and_fails_with_the_old_one(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana = _user_id(client, "ana@example.com", admin)
    client.patch(f"{ADMIN_USERS}/{ana}", json={"email": "ana.new@example.com"}, headers=admin)
    assert (
        client.post(LOGIN, json={"email": "ana.new@example.com", "password": "supersecret"})
    ).status_code == 200
    assert (
        client.post(LOGIN, json={"email": "ana@example.com", "password": "supersecret"})
    ).status_code == 401


def test_token_issued_before_an_email_change_keeps_working(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana_headers = login_headers(client, "ana@example.com")
    ana = _my_id(client, ana_headers)
    client.patch(f"{ADMIN_USERS}/{ana}", json={"email": "ana.new@example.com"}, headers=admin)
    me = client.get(ME, headers=ana_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "ana.new@example.com"


def test_users_me_reflects_the_name_changed_by_an_admin(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    register(client, "ana@example.com")
    ana_headers = login_headers(client, "ana@example.com")
    ana = _my_id(client, ana_headers)
    client.patch(f"{ADMIN_USERS}/{ana}", json={"full_name": "Ana Maria"}, headers=admin)
    assert client.get(ME, headers=ana_headers).json()["full_name"] == "Ana Maria"


def test_admin_edits_own_name_and_email(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    me = _my_id(client, admin)
    response = client.patch(
        f"{ADMIN_USERS}/{me}",
        json={"full_name": "Root Admin", "email": "root@example.com"},
        headers=admin,
    )
    assert response.status_code == 200
    assert (response.json()["full_name"], response.json()["role"]) == ("Root Admin", "admin")
    assert client.get(ME, headers=admin).json()["email"] == "root@example.com"


def test_admin_self_lockout_still_applies_when_name_is_sent(
    client: TestClient, session: Session
) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    me = _my_id(client, admin)
    response = client.patch(
        f"{ADMIN_USERS}/{me}", json={"full_name": "Root", "is_active": False}, headers=admin
    )
    assert response.status_code == 409
    assert client.get(ME, headers=admin).json()["full_name"] == "Ana Perez"


def test_profile_edit_is_forbidden_for_non_admins_and_anonymous(
    client: TestClient, session: Session
) -> None:
    organizer = make_user(client, session, "org@example.com", Role.ORGANIZER)
    body = {"full_name": "Hacker", "email": "h@example.com"}
    assert client.patch(f"{ADMIN_USERS}/1", json=body, headers=organizer).status_code == 403
    assert client.patch(f"{ADMIN_USERS}/1", json=body).status_code == 401


def test_profile_edit_of_unknown_user_is_not_found(client: TestClient, session: Session) -> None:
    admin = make_user(client, session, "admin@example.com", Role.ADMIN)
    response = client.patch(f"{ADMIN_USERS}/999", json={"full_name": "Ghost"}, headers=admin)
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_openapi_documents_profile_fields_and_both_conflict_examples(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/api/v1/admin/users/{user_id}"]["patch"]
    assert operation["summary"] == "Update a user's profile, role or active flag"
    conflict_examples = operation["responses"]["409"]["content"]["application/json"]["examples"]
    assert {key: value["value"] for key, value in conflict_examples.items()} == {
        "email_taken": {"detail": "Email already registered"},
        "self_lockout": {"detail": "Admins cannot demote or deactivate their own account"},
    }
    schema_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    properties = spec["components"]["schemas"][schema_ref.rsplit("/", 1)[-1]]["properties"]
    assert set(properties) == {"full_name", "email", "role", "is_active"}
    assert "422" in operation["responses"]
