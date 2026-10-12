"""Cache policy per aggregate: namespace, keys, TTL and invalidation live together here.

Use cases only invalidate through these objects and cached readers only look up and store
through them, so no other module knows a key shape, a namespace or a TTL.
"""

import hashlib

from app.application.ports import (
    EVENTS_NAMESPACE,
    SESSIONS_NAMESPACE,
    SPEAKERS_NAMESPACE,
    Cache,
)
from app.domain.enums import EventStatus

ABSENT_TEXT_TOKEN = "-"
ANY_STATUS_TOKEN = "any"


def text_digest(text: str | None) -> str:
    """Fixed-length cache-key part for a search text; user input never enters a key raw."""
    if text is None:
        return ABSENT_TEXT_TOKEN
    return hashlib.sha256(text.strip().encode()).hexdigest()


class _NamespaceCache:
    def __init__(self, cache: Cache, namespace: str, ttl_seconds: int) -> None:
        self._cache = cache
        self._namespace = namespace
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> str | None:
        return self._cache.get(self._namespace, key)

    def put(self, key: str, payload: str) -> None:
        self._cache.set(self._namespace, key, payload, self._ttl_seconds)

    def invalidate(self) -> None:
        self._cache.invalidate(self._namespace)


class EventCache(_NamespaceCache):
    """Public event catalogue pages. Removing an event also drops its cached schedule."""

    def __init__(self, cache: Cache, ttl_seconds: int) -> None:
        super().__init__(cache, EVENTS_NAMESPACE, ttl_seconds)

    @staticmethod
    def list_key(q: str | None, status: EventStatus | None, page: int, size: int) -> str:
        status_part = status.value if status else ANY_STATUS_TOKEN
        return f"list:{text_digest(q)}:{status_part}:{page}:{size}"

    def invalidate_with_sessions(self) -> None:
        self.invalidate()
        self._cache.invalidate(SESSIONS_NAMESPACE)


class SessionCache(_NamespaceCache):
    """Per-event schedules, without any per-viewer field."""

    def __init__(self, cache: Cache, ttl_seconds: int) -> None:
        super().__init__(cache, SESSIONS_NAMESPACE, ttl_seconds)

    @staticmethod
    def schedule_key(event_id: int) -> str:
        return f"event:{event_id}"


class SpeakerCache(_NamespaceCache):
    """Speaker directory pages and details. A speaker change also drops cached schedules."""

    def __init__(self, cache: Cache, ttl_seconds: int) -> None:
        super().__init__(cache, SPEAKERS_NAMESPACE, ttl_seconds)

    @staticmethod
    def list_key(q: str | None, page: int, size: int) -> str:
        return f"list:{text_digest(q)}:{page}:{size}"

    @staticmethod
    def detail_key(speaker_id: int) -> str:
        return f"detail:{speaker_id}"

    def invalidate_with_sessions(self) -> None:
        self.invalidate()
        self._cache.invalidate(SESSIONS_NAMESPACE)
