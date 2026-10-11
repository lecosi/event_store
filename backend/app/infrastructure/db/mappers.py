"""Row -> domain entity mappings shared by the SQL repositories."""

from app.domain.event import Event, ensure_utc
from app.domain.registration import Registration
from app.domain.session import Session as SessionEntity
from app.domain.speaker import Speaker
from app.domain.user import UserAccount
from app.infrastructure.db.models import Event as EventRow
from app.infrastructure.db.models import Registration as RegistrationRow
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import Speaker as SpeakerRow
from app.infrastructure.db.models import User as UserRow


def event_to_domain(row: EventRow) -> Event:
    return Event(
        id=row.id,
        name=row.name,
        description=row.description,
        location=row.location,
        start_at=ensure_utc(row.start_at),
        end_at=ensure_utc(row.end_at),
        capacity=row.capacity,
        status=row.status,
        organizer_id=row.organizer_id,
    )


def session_to_domain(row: SessionRow) -> SessionEntity:
    return SessionEntity(
        id=row.id,
        event_id=row.event_id,
        speaker_id=row.speaker_id,
        title=row.title,
        start_at=ensure_utc(row.start_at),
        end_at=ensure_utc(row.end_at),
        capacity=row.capacity,
    )


def speaker_to_domain(row: SpeakerRow) -> Speaker:
    return Speaker(id=row.id, name=row.name, bio=row.bio, email=row.email)


def registration_to_domain(row: RegistrationRow) -> Registration:
    return Registration(
        id=row.id,
        user_id=row.user_id,
        event_id=row.event_id,
        created_at=ensure_utc(row.created_at),
    )


def user_to_domain(row: UserRow) -> UserAccount:
    return UserAccount(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        role=row.role,
        is_active=row.is_active,
    )
