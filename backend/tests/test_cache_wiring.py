import pytest

from app.api.dependencies import get_cache
from app.core.config import Settings
from app.infrastructure.cache.null_cache import NullCache
from app.infrastructure.cache.redis_cache import RedisCache

pytestmark = pytest.mark.unit

VALID_SECRET = "test-only-secret-0123456789-0123456789"


def settings_with(redis_url: str | None) -> Settings:
    return Settings(jwt_secret=VALID_SECRET, redis_url=redis_url, _env_file=None)  # type: ignore[call-arg]


def test_cache_is_a_no_op_when_redis_url_is_unset() -> None:
    assert isinstance(get_cache(settings_with(None)), NullCache)


def test_cache_is_redis_backed_when_redis_url_is_set() -> None:
    assert isinstance(get_cache(settings_with("redis://localhost:6399/0")), RedisCache)


def test_cache_instance_is_shared_across_calls() -> None:
    settings = settings_with("redis://localhost:6399/1")
    assert get_cache(settings) is get_cache(settings)
