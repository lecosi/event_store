"""Read-side contracts the API depends on; services and their cached decorators implement them."""

from typing import Protocol

from app.domain.enums import EventStatus
from app.domain.event import EventPage
from app.domain.session import SessionWithSpeaker
from app.domain.speaker import Speaker, SpeakerPage
from app.domain.user import UserAccount


class EventCatalogue(Protocol):
    def list(
        self,
        viewer: UserAccount | None,
        q: str | None = None,
        status: EventStatus | None = None,
        page: int = 1,
        size: int = 10,
    ) -> EventPage: ...


class SpeakerDirectory(Protocol):
    def get(self, speaker_id: int) -> Speaker: ...

    def list_page(self, q: str | None = None, page: int = 1, size: int = 10) -> SpeakerPage: ...


class EventSchedule(Protocol):
    def list_for_event(self, event_id: int) -> list[SessionWithSpeaker]: ...
