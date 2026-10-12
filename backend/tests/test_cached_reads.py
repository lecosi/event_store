import pytest
from pydantic import BaseModel, TypeAdapter

from app.application.cache_policy import SpeakerCache, text_digest
from app.application.ports import SPEAKERS_NAMESPACE
from app.infrastructure.cache.read_through import read_through
from tests.fakes import FakeCache

pytestmark = pytest.mark.unit


class Payload(BaseModel):
    id: int
    name: str


PAYLOAD = TypeAdapter(Payload)
PAYLOADS = TypeAdapter(list[Payload])


class Builder[T]:
    def __init__(self, value: T | Exception) -> None:
        self.value = value
        self.calls = 0

    def __call__(self) -> T:
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def test_miss_builds_and_stores_value_with_ttl() -> None:
    cache = FakeCache()
    build = Builder(Payload(id=1, name="Ada"))
    result = read_through(SpeakerCache(cache, 42), "detail:1", PAYLOAD, build)
    assert result == Payload(id=1, name="Ada")
    assert build.calls == 1
    assert [(s[0], s[1], s[3]) for s in cache.sets] == [(SPEAKERS_NAMESPACE, "detail:1", 42)]


def test_hit_returns_cached_value_without_building() -> None:
    cache = FakeCache()
    cache.set(SPEAKERS_NAMESPACE, "detail:1", '{"id":1,"name":"Cached"}', 60)
    build = Builder(Payload(id=1, name="Fresh"))
    result = read_through(SpeakerCache(cache, 60), "detail:1", PAYLOAD, build)
    assert result == Payload(id=1, name="Cached")
    assert build.calls == 0


def test_second_read_is_served_from_the_stored_entry() -> None:
    cache = FakeCache()
    build = Builder([Payload(id=1, name="Ada"), Payload(id=2, name="Bo")])
    first = read_through(SpeakerCache(cache, 60), "list", PAYLOADS, build)
    second = read_through(SpeakerCache(cache, 60), "list", PAYLOADS, build)
    assert first == second
    assert build.calls == 1


@pytest.mark.parametrize("corrupt", ["not json", '{"id":"x"}', "", "[]"])
def test_corrupt_payload_falls_back_to_build_and_is_overwritten(corrupt: str) -> None:
    cache = FakeCache()
    cache.set(SPEAKERS_NAMESPACE, "detail:1", corrupt, 60)
    build = Builder(Payload(id=1, name="Fresh"))
    result = read_through(SpeakerCache(cache, 60), "detail:1", PAYLOAD, build)
    assert result == Payload(id=1, name="Fresh")
    assert build.calls == 1
    assert cache.get(SPEAKERS_NAMESPACE, "detail:1") == '{"id":1,"name":"Fresh"}'


def test_build_exception_propagates_and_nothing_is_cached() -> None:
    cache = FakeCache()
    build: Builder[Payload] = Builder(LookupError("missing"))
    with pytest.raises(LookupError):
        read_through(SpeakerCache(cache, 60), "detail:9", PAYLOAD, build)
    assert cache.sets == []


def test_digest_of_missing_text_differs_from_digest_of_empty_text() -> None:
    assert text_digest(None) != text_digest("")


def test_digest_is_fixed_length_hex_and_never_echoes_input() -> None:
    digest = text_digest("grace:../*")
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")
    assert text_digest("grace") != text_digest("hopper")


def test_digest_ignores_surrounding_whitespace() -> None:
    assert text_digest("  grace ") == text_digest("grace")
