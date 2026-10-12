import pytest

from app.application.cache_policy import EventCache, SessionCache, SpeakerCache, text_digest
from app.application.ports import EVENTS_NAMESPACE, SESSIONS_NAMESPACE, SPEAKERS_NAMESPACE
from app.domain.enums import EventStatus
from tests.fakes import FakeCache

pytestmark = pytest.mark.unit


def test_event_list_key_carries_digest_status_page_and_size() -> None:
    key = EventCache.list_key("python", EventStatus.PUBLISHED, 2, 5)
    assert key == f"list:{text_digest('python')}:published:2:5"


def test_event_list_key_uses_any_token_without_status() -> None:
    assert EventCache.list_key(None, None, 1, 10) == "list:-:any:1:10"


def test_speaker_keys_for_list_and_detail() -> None:
    assert SpeakerCache.list_key(None, 3, 20) == "list:-:3:20"
    assert SpeakerCache.detail_key(7) == "detail:7"


def test_session_schedule_key_is_per_event() -> None:
    assert SessionCache.schedule_key(4) == "event:4"


def test_put_stores_under_own_namespace_with_configured_ttl() -> None:
    backend = FakeCache()
    SpeakerCache(backend, 33).put("detail:1", "payload")
    assert backend.sets == [(SPEAKERS_NAMESPACE, "detail:1", "payload", 33)]


def test_event_invalidation_with_sessions_drops_events_then_sessions() -> None:
    backend = FakeCache()
    EventCache(backend, 1).invalidate_with_sessions()
    assert backend.invalidations == [EVENTS_NAMESPACE, SESSIONS_NAMESPACE]


def test_speaker_invalidation_with_sessions_drops_speakers_then_sessions() -> None:
    backend = FakeCache()
    SpeakerCache(backend, 1).invalidate_with_sessions()
    assert backend.invalidations == [SPEAKERS_NAMESPACE, SESSIONS_NAMESPACE]


def test_session_invalidation_drops_only_sessions() -> None:
    backend = FakeCache()
    SessionCache(backend, 1).invalidate()
    assert backend.invalidations == [SESSIONS_NAMESPACE]
