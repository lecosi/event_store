"""Speaker entity (pure domain, no framework imports)."""

from dataclasses import dataclass, replace
from math import ceil


@dataclass(frozen=True)
class SpeakerDetails:
    """Editable attributes of a speaker. ``email`` is optional but unique when present."""

    name: str
    bio: str
    email: str | None


@dataclass
class Speaker:
    name: str
    bio: str
    email: str | None
    id: int | None = None

    def with_details(self, details: SpeakerDetails) -> "Speaker":
        return replace(self, name=details.name, bio=details.bio, email=details.email)


@dataclass(frozen=True)
class SpeakerPage:
    items: list[Speaker]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size) if self.total else 0
