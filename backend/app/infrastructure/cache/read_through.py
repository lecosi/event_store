"""Read-through caching of serialized read payloads."""

from collections.abc import Callable
from typing import Protocol

from pydantic import TypeAdapter, ValidationError


class PayloadStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def put(self, key: str, payload: str) -> None: ...


def read_through[T](
    store: PayloadStore,
    key: str,
    adapter: TypeAdapter[T],
    build: Callable[[], T],
) -> T:
    """Return the cached payload, or build it, store it and return it.

    A corrupt entry counts as a miss. Whatever ``build`` raises propagates uncached.
    """
    cached = store.get(key)
    if cached is not None:
        try:
            return adapter.validate_json(cached)
        except ValidationError:
            pass
    value = build()
    store.put(key, adapter.dump_json(value).decode())
    return value
