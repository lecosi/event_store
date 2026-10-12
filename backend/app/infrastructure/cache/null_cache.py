class NullCache:
    """No-op cache: every read is a miss. Used when no cache backend is configured."""

    def get(self, namespace: str, key: str) -> str | None:
        return None

    def set(self, namespace: str, key: str, value: str, ttl_seconds: int) -> None:
        return None

    def invalidate(self, namespace: str) -> None:
        return None
