import logging

import pytest
import redis

from app.infrastructure.cache import redis_cache as redis_cache_module
from app.infrastructure.cache.null_cache import NullCache
from app.infrastructure.cache.redis_cache import RedisCache

pytestmark = pytest.mark.unit


class StubRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.fail_with: Exception | None = None

    def get(self, name: str) -> str | None:
        self._raise_if_down()
        return self.data.get(name)

    def setex(self, name: str, time: int, value: str) -> None:
        self._raise_if_down()
        self.data[name] = value
        self.expirations[name] = time

    def incr(self, name: str) -> int:
        self._raise_if_down()
        value = int(self.data.get(name, "0")) + 1
        self.data[name] = str(value)
        return value

    def _raise_if_down(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with


@pytest.fixture
def client() -> StubRedis:
    return StubRedis()


@pytest.fixture
def cache(client: StubRedis) -> RedisCache:
    return RedisCache(client)  # type: ignore[arg-type]


def test_missing_entry_is_a_miss(cache):
    assert cache.get("events", "page=1") is None


def test_stored_entry_is_returned(cache):
    cache.set("events", "page=1", "payload", ttl_seconds=60)
    assert cache.get("events", "page=1") == "payload"


def test_entries_of_other_keys_and_namespaces_are_isolated(cache):
    cache.set("events", "page=1", "events-payload", ttl_seconds=60)
    cache.set("speakers", "page=1", "speakers-payload", ttl_seconds=60)
    assert cache.get("events", "page=2") is None
    assert cache.get("speakers", "page=1") == "speakers-payload"


def test_ttl_is_passed_to_the_client(cache, client):
    cache.set("sessions", "event=3", "payload", ttl_seconds=120)
    assert list(client.expirations.values()) == [120]


def test_invalidation_makes_previous_entries_unreachable(cache):
    cache.set("events", "page=1", "stale", ttl_seconds=60)
    cache.invalidate("events")
    assert cache.get("events", "page=1") is None


def test_entries_written_after_invalidation_are_reachable(cache):
    cache.set("events", "page=1", "stale", ttl_seconds=60)
    cache.invalidate("events")
    cache.set("events", "page=1", "fresh", ttl_seconds=60)
    assert cache.get("events", "page=1") == "fresh"


def test_invalidation_only_affects_its_namespace(cache):
    cache.set("events", "page=1", "events-payload", ttl_seconds=60)
    cache.set("speakers", "page=1", "speakers-payload", ttl_seconds=60)
    cache.invalidate("events")
    assert cache.get("speakers", "page=1") == "speakers-payload"


def test_invalidation_increments_the_namespace_version_counter(cache, client):
    cache.invalidate("events")
    cache.invalidate("events")
    assert client.data["events:version"] == "2"


@pytest.mark.parametrize("error", [redis.ConnectionError("down"), redis.TimeoutError("slow")])
class TestOutage:
    def test_get_degrades_to_a_miss(self, cache, client, error):
        client.fail_with = error
        assert cache.get("events", "page=1") is None

    def test_set_does_not_raise(self, cache, client, error):
        client.fail_with = error
        cache.set("events", "page=1", "payload", ttl_seconds=60)

    def test_invalidate_does_not_raise(self, cache, client, error):
        client.fail_with = error
        cache.invalidate("events")


@pytest.fixture
def cache_logger_enabled():
    cache_logger = logging.getLogger(redis_cache_module.__name__)
    was_disabled = cache_logger.disabled
    cache_logger.disabled = False
    yield
    cache_logger.disabled = was_disabled


def test_outage_is_logged_as_a_warning(cache, client, caplog, cache_logger_enabled):
    client.fail_with = redis.ConnectionError("down")
    with caplog.at_level(logging.WARNING):
        cache.get("events", "page=1")
    assert any(record.levelno == logging.WARNING for record in caplog.records)


@pytest.mark.parametrize(
    "operation",
    [
        lambda cache: cache.get("events", "page=1"),
        lambda cache: cache.set("events", "page=1", "payload", ttl_seconds=60),
        lambda cache: cache.invalidate("events"),
    ],
    ids=["get", "set", "invalidate"],
)
class TestOutageLogging:
    def test_warning_carries_no_traceback(
        self, cache, client, caplog, cache_logger_enabled, operation
    ):
        client.fail_with = redis.ConnectionError("connection refused")
        with caplog.at_level(logging.WARNING):
            operation(cache)
        assert caplog.records
        assert all(record.exc_info is None for record in caplog.records)

    def test_warning_names_the_failure(
        self, cache, client, caplog, cache_logger_enabled, operation
    ):
        client.fail_with = redis.ConnectionError("connection refused")
        with caplog.at_level(logging.WARNING):
            operation(cache)
        assert "connection refused" in caplog.text


def test_os_level_socket_errors_also_degrade(cache, client):
    client.fail_with = ConnectionResetError("reset")
    assert cache.get("events", "page=1") is None


def test_from_url_builds_a_cache_without_connecting():
    assert isinstance(RedisCache.from_url("redis://localhost:6399/0"), RedisCache)


def test_null_cache_never_hits():
    cache = NullCache()
    cache.set("events", "page=1", "payload", ttl_seconds=60)
    assert cache.get("events", "page=1") is None


def test_null_cache_invalidate_is_a_no_op():
    NullCache().invalidate("events")
