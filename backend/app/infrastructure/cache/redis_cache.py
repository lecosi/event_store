import logging

import redis

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT_SECONDS = 0.5
_COMMAND_TIMEOUT_SECONDS = 0.5


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


class RedisCache:
    """Redis-backed cache with per-namespace versioning.

    Entries live under a key that embeds the namespace's current version, so
    invalidating a namespace is a single INCR: older entries become unreachable and
    expire on their own TTL. Any Redis failure is logged and treated as a miss/no-op.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisCache":
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            socket_timeout=_COMMAND_TIMEOUT_SECONDS,
        )
        return cls(client)

    def get(self, namespace: str, key: str) -> str | None:
        try:
            return _as_text(self._client.get(self._entry_key(namespace, key)))
        except (redis.RedisError, OSError):
            logger.warning("cache get failed for %s; treating as a miss", namespace, exc_info=True)
            return None

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.setex(self._entry_key(namespace, key), ttl_seconds, value)
        except (redis.RedisError, OSError):
            logger.warning("cache set failed for %s; skipping", namespace, exc_info=True)

    def invalidate(self, namespace: str) -> None:
        try:
            self._client.incr(self._version_key(namespace))
        except (redis.RedisError, OSError):
            logger.warning("cache invalidation failed for %s", namespace, exc_info=True)

    def _entry_key(self, namespace: str, key: str) -> str:
        version = _as_text(self._client.get(self._version_key(namespace))) or "0"
        return f"{namespace}:v{version}:{key}"

    @staticmethod
    def _version_key(namespace: str) -> str:
        return f"{namespace}:version"
