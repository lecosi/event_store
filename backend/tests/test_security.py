from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.api.dependencies import get_password_hasher
from app.application.errors import InvalidTokenError
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.security.password_hasher import Argon2PasswordHasher

KEY = "test-secret-key-0123456789-0123456789"
OTHER_KEY = "other-secret-key-0123456789-0123456789"


def test_hash_is_argon2_and_verifies() -> None:
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("supersecret")
    assert hashed.startswith("$argon2")
    assert "supersecret" not in hashed
    assert hasher.verify("supersecret", hashed)
    assert not hasher.verify("other-password", hashed)
    assert hasher.hash("supersecret") != hashed


def test_token_roundtrip() -> None:
    service = JwtTokenService(KEY, "HS256", 5)
    assert service.read_subject(service.create_access_token(7)) == 7


def test_token_iat_and_exp_follow_the_injected_clock() -> None:
    issued_at = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
    service = JwtTokenService(KEY, "HS256", 5, clock=lambda: issued_at)
    claims = jwt.decode(
        service.create_access_token(7),
        KEY,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )
    assert claims["iat"] == int(issued_at.timestamp())
    assert claims["exp"] == int((issued_at + timedelta(minutes=5)).timestamp())


def test_token_issued_by_a_past_clock_is_expired() -> None:
    long_ago = datetime(2000, 1, 1, tzinfo=UTC)
    service = JwtTokenService(KEY, "HS256", 5, clock=lambda: long_ago)
    with pytest.raises(InvalidTokenError):
        service.read_subject(service.create_access_token(7))


def test_expired_token_is_rejected() -> None:
    service = JwtTokenService(KEY, "HS256", -1)
    with pytest.raises(InvalidTokenError):
        service.read_subject(service.create_access_token(7))


def test_tampered_or_foreign_tokens_are_rejected() -> None:
    service = JwtTokenService(KEY, "HS256", 5)
    with pytest.raises(InvalidTokenError):
        service.read_subject("not-a-jwt")
    with pytest.raises(InvalidTokenError):
        service.read_subject(JwtTokenService(OTHER_KEY, "HS256", 5).create_access_token(7))


def test_token_without_subject_or_exp_is_rejected() -> None:
    service = JwtTokenService(KEY, "HS256", 5)
    no_sub = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}, KEY, "HS256")
    no_exp = jwt.encode({"sub": "7"}, KEY, "HS256")
    bad_sub = jwt.encode(
        {"sub": "abc", "exp": datetime.now(UTC) + timedelta(minutes=5)}, KEY, "HS256"
    )
    for token in (no_sub, no_exp, bad_sub):
        with pytest.raises(InvalidTokenError):
            service.read_subject(token)


def test_password_hasher_dependency_is_built_once() -> None:
    assert get_password_hasher() is get_password_hasher()
