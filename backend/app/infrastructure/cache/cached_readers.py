"""Cached decorators of the read use cases; routers call them like the plain services."""

from pydantic import TypeAdapter

from app.application.cache_policy import EventCache, SessionCache, SpeakerCache
from app.application.event_service import is_public_view
from app.application.readers import EventCatalogue, EventSchedule, SpeakerDirectory
from app.domain.enums import EventStatus
from app.domain.event import EventPage
from app.domain.session import SessionWithSpeaker
from app.domain.speaker import Speaker, SpeakerPage
from app.domain.user import UserAccount
from app.infrastructure.cache.read_through import read_through

EVENT_PAGE = TypeAdapter(EventPage)
SPEAKER_PAGE = TypeAdapter(SpeakerPage)
SPEAKER = TypeAdapter(Speaker)
SCHEDULE = TypeAdapter(list[SessionWithSpeaker])


class CachedEventCatalogue:
    """Serves the public view from cache; organizing viewers always read the database."""

    def __init__(self, inner: EventCatalogue, cache: EventCache) -> None:
        self._inner = inner
        self._cache = cache

    def list(
        self,
        viewer: UserAccount | None,
        q: str | None = None,
        status: EventStatus | None = None,
        page: int = 1,
        size: int = 10,
    ) -> EventPage:
        def build() -> EventPage:
            return self._inner.list(viewer, q=q, status=status, page=page, size=size)

        if not is_public_view(viewer):
            return build()
        key = self._cache.list_key(q, status, page, size)
        return read_through(self._cache, key, EVENT_PAGE, build)


class CachedSpeakerDirectory:
    def __init__(self, inner: SpeakerDirectory, cache: SpeakerCache) -> None:
        self._inner = inner
        self._cache = cache

    def get(self, speaker_id: int) -> Speaker:
        key = self._cache.detail_key(speaker_id)
        return read_through(self._cache, key, SPEAKER, lambda: self._inner.get(speaker_id))

    def list_page(self, q: str | None = None, page: int = 1, size: int = 10) -> SpeakerPage:
        key = self._cache.list_key(q, page, size)
        return read_through(
            self._cache, key, SPEAKER_PAGE, lambda: self._inner.list_page(q=q, page=page, size=size)
        )


class CachedEventSchedule:
    def __init__(self, inner: EventSchedule, cache: SessionCache) -> None:
        self._inner = inner
        self._cache = cache

    def list_for_event(self, event_id: int) -> list[SessionWithSpeaker]:
        key = self._cache.schedule_key(event_id)
        return read_through(
            self._cache, key, SCHEDULE, lambda: self._inner.list_for_event(event_id)
        )
