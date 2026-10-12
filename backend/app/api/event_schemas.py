"""Event DTOs. Only the public attributes of an event are exposed."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.speaker_schemas import SessionResponse
from app.domain.enums import EventStatus


class EventRequest(BaseModel):
    """Editable attributes of an event (create or full replace)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "PyCon Latam 2030",
                    "description": "Two days of talks about Python.",
                    "location": "Medellin Convention Center",
                    "start_at": "2030-05-20T09:00:00Z",
                    "end_at": "2030-05-21T18:00:00Z",
                    "capacity": 300,
                }
            ]
        }
    )

    name: str = Field(
        min_length=1, max_length=200, description="Event name.", examples=["PyCon Latam 2030"]
    )
    description: str = Field(
        default="",
        max_length=5000,
        description="Free-text description.",
        examples=["Two days of talks about Python."],
    )
    location: str = Field(
        min_length=1,
        max_length=255,
        description="Where the event takes place.",
        examples=["Medellin Convention Center"],
    )
    start_at: datetime = Field(
        description="Start (ISO 8601). Must be in the future when creating.",
        examples=["2030-05-20T09:00:00Z"],
    )
    end_at: datetime = Field(
        description="End (ISO 8601); must be after `start_at`.",
        examples=["2030-05-21T18:00:00Z"],
    )
    capacity: int = Field(
        ge=1,
        description=(
            "Maximum number of attendees. On update it cannot be lower than the current "
            "registrations or the largest session capacity."
        ),
        examples=[300],
    )


class EventStatusRequest(BaseModel):
    """Target status for a lifecycle transition."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "published"}]})

    status: EventStatus = Field(
        description=(
            "Target status. Allowed transitions: draft -> published | cancelled; "
            "published -> finished | cancelled; cancelled and finished are final."
        ),
        examples=["published"],
    )


class EventResponse(BaseModel):
    """An event."""

    id: int = Field(description="Event identifier.", examples=[1])
    name: str = Field(description="Event name.", examples=["PyCon Latam 2030"])
    description: str = Field(
        description="Free-text description.", examples=["Two days of talks about Python."]
    )
    location: str = Field(
        description="Where the event takes place.", examples=["Medellin Convention Center"]
    )
    start_at: datetime = Field(description="Start (ISO 8601).", examples=["2030-05-20T09:00:00Z"])
    end_at: datetime = Field(description="End (ISO 8601).", examples=["2030-05-21T18:00:00Z"])
    capacity: int = Field(description="Maximum number of attendees.", examples=[300])
    status: EventStatus = Field(
        description="Lifecycle status. Only `published` events are public.",
        examples=["published"],
    )
    organizer_id: int = Field(description="User who owns the event.", examples=[1])


class EventDetailResponse(EventResponse):
    """An event with its sessions and the availability for the caller."""

    sessions: list[SessionResponse] = Field(
        default=[], description="Sessions scheduled in the event, ordered by start time."
    )
    registered_count: int = Field(
        default=0, description="Number of attendees currently registered.", examples=[42]
    )
    available_spots: int = Field(
        default=0,
        description="Remaining seats: capacity minus registrations (never negative).",
        examples=[258],
    )
    is_registered: bool = Field(
        default=False,
        description="Whether the authenticated caller is registered (always false if anonymous).",
        examples=[False],
    )


class RegistrationResponse(BaseModel):
    """A registration of a user to an event."""

    user_id: int = Field(description="Registered user.", examples=[2])
    event_id: int = Field(description="Event the user registered to.", examples=[1])
    created_at: datetime = Field(
        description="When the registration was made (ISO 8601).", examples=["2030-01-10T15:30:00Z"]
    )


class SessionRegistrationResponse(BaseModel):
    """An enrollment of a user in a session."""

    user_id: int = Field(description="Enrolled user.", examples=[2])
    session_id: int = Field(description="Session the user enrolled in.", examples=[1])
    created_at: datetime = Field(
        description="When the enrollment was made (ISO 8601).", examples=["2030-01-10T15:30:00Z"]
    )


class RegisteredEventResponse(EventResponse):
    """An event the caller is registered to."""

    registered_at: datetime = Field(
        description="When the caller registered (ISO 8601).", examples=["2030-01-10T15:30:00Z"]
    )


class RegisteredEventPageResponse(BaseModel):
    """One page of the caller's registered events."""

    items: list[RegisteredEventResponse] = Field(description="Events on this page.")
    total: int = Field(description="Total registered events across all pages.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])


class EventPageResponse(BaseModel):
    """One page of events."""

    items: list[EventResponse] = Field(description="Events on this page.")
    total: int = Field(description="Total events matching the filters.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])
