"""Participants report DTOs."""

from datetime import datetime

from pydantic import BaseModel, Field


class ParticipantResponse(BaseModel):
    """One person registered to one event."""

    full_name: str = Field(description="Full name of the registered user.", examples=["Ana Gomez"])
    email: str = Field(
        description="Email address of the registered user.", examples=["ana.gomez@example.com"]
    )
    event_name: str = Field(description="Name of the event.", examples=["PyCon Latam 2030"])


class ParticipantPageResponse(BaseModel):
    """One page of the participants report."""

    items: list[ParticipantResponse] = Field(
        description=(
            "Participants on this page, ordered by event start, event, registration date "
            "and registration."
        )
    )
    total: int = Field(description="Total participants matching the filters.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])


class SessionParticipantResponse(BaseModel):
    """One person enrolled in one session."""

    full_name: str = Field(description="Full name of the enrolled user.", examples=["Ana Gomez"])
    email: str = Field(
        description="Email address of the enrolled user.", examples=["ana.gomez@example.com"]
    )
    event_name: str = Field(
        description="Name of the event the session belongs to.", examples=["PyCon Latam 2030"]
    )
    session_title: str = Field(description="Title of the session.", examples=["Keynote"])
    session_start: datetime = Field(
        description="Start of the session (UTC).", examples=["2030-05-10T09:00:00Z"]
    )


class SessionParticipantPageResponse(BaseModel):
    """One page of the session participants report."""

    items: list[SessionParticipantResponse] = Field(
        description=(
            "Enrolled people on this page, ordered by session start, session, enrollment date "
            "and enrollment."
        )
    )
    total: int = Field(description="Total enrollments matching the filters.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])
