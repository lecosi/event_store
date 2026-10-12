"""Finish the published events whose end date has already passed.

Usage (from ``backend/``):  ``python -m scripts.close_past_events``
Safe to run repeatedly: events that are still in progress, drafts, cancelled and already
finished events are never touched.
"""

from sqlmodel import Session

from app.application.cache_policy import EventCache
from app.application.close_past_events import close_past_events
from app.application.ports import Cache
from app.core.config import get_settings
from app.infrastructure.cache.null_cache import NullCache
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.session import get_engine
from app.infrastructure.db.unit_of_work import SqlUnitOfWork


def _cache() -> Cache:
    redis_url = get_settings().redis_url
    return RedisCache.from_url(redis_url) if redis_url else NullCache()


def main() -> int:
    with Session(get_engine()) as session:
        cache = EventCache(_cache(), get_settings().cache_ttl_events_seconds)
        closed = close_past_events(SqlEventRepository(session), SqlUnitOfWork(session), cache)
    print(f"Finished events: {closed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
