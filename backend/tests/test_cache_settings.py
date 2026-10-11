import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_SECRET = "test-only-secret-0123456789-0123456789"


@pytest.fixture(autouse=True)
def _valid_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", VALID_SECRET)
    for name in (
        "REDIS_URL",
        "CACHE_TTL_EVENTS_SECONDS",
        "CACHE_TTL_SESSIONS_SECONDS",
        "CACHE_TTL_SPEAKERS_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


def build_settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_redis_url_is_unset_by_default():
    assert build_settings().redis_url is None


def test_ttl_defaults_are_sixty_one_twenty_and_three_hundred_seconds():
    settings = build_settings()
    assert settings.cache_ttl_events_seconds == 60
    assert settings.cache_ttl_sessions_seconds == 120
    assert settings.cache_ttl_speakers_seconds == 300


def test_cache_settings_read_environment(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/0")
    monkeypatch.setenv("CACHE_TTL_EVENTS_SECONDS", "15")
    monkeypatch.setenv("CACHE_TTL_SESSIONS_SECONDS", "25")
    monkeypatch.setenv("CACHE_TTL_SPEAKERS_SECONDS", "35")
    settings = build_settings()
    assert settings.redis_url == "redis://cache:6379/0"
    assert settings.cache_ttl_events_seconds == 15
    assert settings.cache_ttl_sessions_seconds == 25
    assert settings.cache_ttl_speakers_seconds == 35


@pytest.mark.parametrize(
    "name",
    [
        "CACHE_TTL_EVENTS_SECONDS",
        "CACHE_TTL_SESSIONS_SECONDS",
        "CACHE_TTL_SPEAKERS_SECONDS",
    ],
)
@pytest.mark.parametrize("value", ["0", "-5"])
def test_non_positive_ttl_is_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        build_settings()
