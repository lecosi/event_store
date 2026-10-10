import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_SECRET = "test-only-secret-0123456789-0123456789"


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("JWT_SECRET", VALID_SECRET)
    settings = Settings()
    assert settings.database_url == "sqlite://"
    assert settings.jwt_secret == VALID_SECRET


def test_short_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s3cret")
    with pytest.raises(ValidationError, match="secrets.token_urlsafe"):
        Settings()


def test_placeholder_jwt_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings()


def test_missing_jwt_secret_fails_instead_of_using_the_placeholder(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_minimum_length_jwt_secret_is_accepted(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    assert Settings().jwt_secret == "x" * 32
