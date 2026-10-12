"""Speaker entity (pure domain, no framework imports)."""

from dataclasses import dataclass, replace

from app.domain.pagination import Page


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


SpeakerPage = Page[Speaker]
