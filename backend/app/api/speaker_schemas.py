"""Speaker and session DTOs."""

from dataclasses import asdict
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.session import SessionWithSpeaker
from app.domain.session_registration import SessionAvailability


class SpeakerRequest(BaseModel):
    """Data of a speaker (create or full replace)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Grace Hopper",
                    "bio": "Computer scientist and Navy rear admiral.",
                    "email": "grace@example.com",
                }
            ]
        }
    )

    name: str = Field(
        min_length=1, max_length=200, description="Full name.", examples=["Grace Hopper"]
    )
    bio: str = Field(
        default="",
        max_length=5000,
        description="Short biography.",
        examples=["Computer scientist and Navy rear admiral."],
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Optional contact email; must be unique among speakers.",
        examples=["grace@example.com"],
    )


class SpeakerResponse(BaseModel):
    """A speaker."""

    id: int = Field(description="Speaker identifier.", examples=[1])
    name: str = Field(description="Full name.", examples=["Grace Hopper"])
    bio: str = Field(description="Short biography.", examples=["Computer scientist."])
    email: str | None = Field(description="Contact email, if any.", examples=["grace@example.com"])


class SpeakerPageResponse(BaseModel):
    """One page of speakers."""

    items: list[SpeakerResponse] = Field(description="Speakers on this page, ordered by name.")
    total: int = Field(description="Total speakers matching the search.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])


class SpeakerRef(BaseModel):
    """Compact speaker reference embedded in a session."""

    id: int = Field(description="Speaker identifier.", examples=[1])
    name: str = Field(description="Full name.", examples=["Grace Hopper"])


class SessionRequest(BaseModel):
    """Data of a session (create or full replace)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Opening keynote",
                    "speaker_id": 1,
                    "start_at": "2030-05-20T10:00:00Z",
                    "end_at": "2030-05-20T11:00:00Z",
                    "capacity": 100,
                }
            ]
        }
    )

    title: str = Field(
        min_length=1, max_length=200, description="Session title.", examples=["Opening keynote"]
    )
    speaker_id: int = Field(description="Identifier of an existing speaker.", examples=[1])
    start_at: datetime = Field(
        description="Start (ISO 8601); must be inside the event dates.",
        examples=["2030-05-20T10:00:00Z"],
    )
    end_at: datetime = Field(
        description="End (ISO 8601); after `start_at` and inside the event dates.",
        examples=["2030-05-20T11:00:00Z"],
    )
    capacity: int = Field(
        description="Seats for the session; between 1 and the event capacity.", examples=[100]
    )


class ScheduledSession(BaseModel):
    """A session of an event: the part that is the same for every viewer (cacheable)."""

    id: int = Field(description="Session identifier.", examples=[1])
    event_id: int = Field(description="Event the session belongs to.", examples=[1])
    title: str = Field(description="Session title.", examples=["Opening keynote"])
    start_at: datetime = Field(description="Start (ISO 8601).", examples=["2030-05-20T10:00:00Z"])
    end_at: datetime = Field(description="End (ISO 8601).", examples=["2030-05-20T11:00:00Z"])
    capacity: int = Field(description="Seats for the session.", examples=[100])
    speaker: SpeakerRef = Field(description="Speaker giving the session.")

    @classmethod
    def from_domain(cls, item: SessionWithSpeaker) -> "ScheduledSession":
        s = item.session
        assert s.id is not None
        return cls(
            id=s.id,
            event_id=s.event_id,
            title=s.title,
            start_at=s.start_at,
            end_at=s.end_at,
            capacity=s.capacity,
            speaker=SpeakerRef(id=s.speaker_id, name=item.speaker_name),
        )


class SessionResponse(ScheduledSession):
    """A session of an event with its enrollment availability for the caller."""

    enrolled_count: int = Field(
        default=0, description="Attendees currently enrolled in the session.", examples=[12]
    )
    available_spots: int = Field(
        default=0,
        description="Remaining seats: session capacity minus enrollments (never negative).",
        examples=[88],
    )
    is_enrolled: bool = Field(
        default=False,
        description="Whether the authenticated caller is enrolled (always false if anonymous).",
        examples=[False],
    )

    @classmethod
    def from_scheduled(
        cls, session: ScheduledSession, availability: SessionAvailability
    ) -> "SessionResponse":
        return cls(**session.model_dump(), **asdict(availability))
