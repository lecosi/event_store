from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.application.clock import utc_now
from app.domain.enums import EventStatus, Role

# Field(sa_type=...) is typed as a type, but SQLAlchemy accepts type instances.
_TZ_DATETIME: Any = DateTime(timezone=True)


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_lower_prefix", text("lower(email) text_pattern_ops")),)

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    full_name: str = Field(max_length=200)
    password_hash: str = Field(max_length=255)
    role: Role = Field(default=Role.ATTENDEE)
    is_active: bool = Field(default=True)


class Event(SQLModel, table=True):
    __tablename__ = "event"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="ck_event_capacity_positive"),
        CheckConstraint("end_at > start_at", name="ck_event_dates_order"),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: str = Field(default="")
    location: str = Field(max_length=255)
    start_at: datetime = Field(sa_type=_TZ_DATETIME)
    end_at: datetime = Field(sa_type=_TZ_DATETIME)
    capacity: int
    status: EventStatus = Field(default=EventStatus.DRAFT, index=True)
    organizer_id: int = Field(foreign_key="users.id", index=True)


class Speaker(SQLModel, table=True):
    __tablename__ = "speaker"
    __table_args__ = (UniqueConstraint("email", name="uq_speaker_email"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    bio: str = Field(default="")
    email: str | None = Field(default=None, max_length=255)


class Session(SQLModel, table=True):
    __tablename__ = "session"
    __table_args__ = (
        CheckConstraint("capacity >= 1", name="ck_session_capacity_positive"),
        CheckConstraint("end_at > start_at", name="ck_session_dates_order"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", ondelete="CASCADE", index=True)
    speaker_id: int = Field(foreign_key="speaker.id", index=True)
    title: str = Field(max_length=200)
    start_at: datetime = Field(sa_type=_TZ_DATETIME)
    end_at: datetime = Field(sa_type=_TZ_DATETIME)
    capacity: int


class Registration(SQLModel, table=True):
    __tablename__ = "registration"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_registration_user_event"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    event_id: int = Field(foreign_key="event.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=_TZ_DATETIME)


class SessionRegistration(SQLModel, table=True):
    __tablename__ = "session_registration"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_session_registration_user_session"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_id: int = Field(foreign_key="session.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=_TZ_DATETIME)
