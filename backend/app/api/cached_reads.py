"""Read-through caching of API response payloads."""

import hashlib
from collections.abc import Callable

from pydantic import TypeAdapter, ValidationError

from app.application.ports import Cache

ABSENT_TEXT_TOKEN = "-"


def text_digest(text: str | None) -> str:
    """Fixed-length cache-key part for a search text; user input never enters a key raw."""
    if text is None:
        return ABSENT_TEXT_TOKEN
    return hashlib.sha256(text.strip().encode()).hexdigest()


def read_through[T](
    cache: Cache,
    namespace: str,
    key: str,
    ttl_seconds: int,
    adapter: TypeAdapter[T],
    build: Callable[[], T],
) -> T:
    """Return the cached payload, or build it, store it and return it.

    A corrupt entry counts as a miss. Whatever ``build`` raises propagates uncached.
    """
    cached = cache.get(namespace, key)
    if cached is not None:
        try:
            return adapter.validate_json(cached)
        except ValidationError:
            pass
    value = build()
    cache.set(namespace, key, adapter.dump_json(value).decode(), ttl_seconds)
    return value
