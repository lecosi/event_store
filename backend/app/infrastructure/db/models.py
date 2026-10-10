from datetime import UTC, datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.domain.enums import EventStatus, Role


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: Role = Field(default=Role.ATTENDEE)
    is_active: bool = Field(default=True)


class Event(SQLModel, table=True):
    __tablename__ = "event"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: str = Field(default="")
    location: str = Field(max_length=255)
    start_at: datetime = Field(sa_type=DateTime(timezone=True))
    end_at: datetime = Field(sa_type=DateTime(timezone=True))
    capacity: int
    status: EventStatus = Field(default=EventStatus.DRAFT, index=True)
    organizer_id: int = Field(foreign_key="users.id", index=True)


class Speaker(SQLModel, table=True):
    __tablename__ = "speaker"
    __table_args__ = (UniqueConstraint("email", name="uq_speaker_email"),)


    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    bio: str = Field(default="")
    email: str = Field(max_length=255)


class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    speaker_id: int = Field(foreign_key="speaker.id", index=True)
    title: str = Field(max_length=200)
    start_at: datetime = Field(sa_type=DateTime(timezone=True))
    end_at: datetime = Field(sa_type=DateTime(timezone=True))
    capacity: int


class Registration(SQLModel, table=True):
    __tablename__ = "registration"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_registration_user_event"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
