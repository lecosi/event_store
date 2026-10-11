"""Load demo data (speakers, events, sessions, attendees) to try the app quickly.

Usage (from ``backend/``):  ``python -m scripts.seed_demo``
Requires the administrator to exist (``python -m scripts.seed``). Idempotent: it does
nothing when the database already contains events.
"""

import os
import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.application.auth_service import AuthService, normalize_email
from app.application.errors import EmailAlreadyRegisteredError
from app.application.event_service import EventService
from app.application.registration_service import RegistrationService
from app.application.session_service import SessionService
from app.application.speaker_service import SpeakerService
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventDetails
from app.domain.session import SessionDetails
from app.domain.speaker import SpeakerDetails
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.registration_repository import SqlRegistrationRepository
from app.infrastructure.db.session import get_engine
from app.infrastructure.db.session_repository import SqlSessionRepository
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.user_repository import SqlUserRepository
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.security.password_hasher import Argon2PasswordHasher

ATTENDEE_PASSWORD = "attendee123"
ATTENDEE_NAMES = {
    "attendee@example.com": "Demo Attendee",
    "attendee1@example.com": "Ana Perez",
    "attendee2@example.com": "Luis Gomez",
    "attendee3@example.com": "Maria Lopez",
    "attendee4@example.com": "Carlos Ruiz",
}
ATTENDEE_EMAILS = list(ATTENDEE_NAMES)

SPEAKERS = [
    SpeakerDetails("Grace Hopper", "Computer scientist and compiler pioneer.", "grace@example.com"),
    SpeakerDetails("Linus Torvalds", "Creator of Linux and Git.", "linus@example.com"),
    SpeakerDetails(
        "Margaret Hamilton", "Lead of the Apollo flight software.", "margaret@example.com"
    ),
]


def _day(days: int, hour: int, hours: int = 1) -> tuple[datetime, datetime]:
    start = (datetime.now(UTC) + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return start, start + timedelta(hours=hours)


def _event(name: str, description: str, location: str, days: int, capacity: int) -> EventDetails:
    start, end = _day(days, 9, hours=8)
    return EventDetails(name, description, location, start, end, capacity)


def main() -> int:
    admin_email = normalize_email(os.environ.get("ADMIN_EMAIL", ""))
    with Session(get_engine()) as db:
        uow = SqlUnitOfWork(db)
        users = SqlUserRepository(db)
        admin = users.get_by_email(admin_email) if admin_email else None
        if admin is None:
            print("Admin not found: run `python -m scripts.seed` first", file=sys.stderr)
            return 1

        events_repo = SqlEventRepository(db)
        events = EventService(events_repo, uow)
        if events.list(admin, size=1).total > 0:
            print("Events already exist: demo data skipped")
            return 0

        speaker_service = SpeakerService(SqlSpeakerRepository(db), uow)
        speakers = [speaker_service.create(admin, details) for details in SPEAKERS]
        sessions = SessionService(
            events_repo, SqlSessionRepository(db), SqlSpeakerRepository(db), uow
        )
        registrations = RegistrationService(events_repo, SqlRegistrationRepository(db), uow)

        hasher = Argon2PasswordHasher()
        auth = AuthService(users, hasher, JwtTokenService("unused", "HS256", 1), uow)
        attendees = []
        for email, full_name in ATTENDEE_NAMES.items():
            try:
                attendees.append(auth.register(email, ATTENDEE_PASSWORD, full_name, Role.ATTENDEE))
            except EmailAlreadyRegisteredError:
                account = users.get_by_email(email)
                assert account is not None
                attendees.append(account)

        def create(details: EventDetails, status: EventStatus | None = None) -> Event:
            event = events.create(admin, details)
            assert event.id is not None
            if status is not None:
                events.change_status(admin, event.id, status)
            return event

        conference = create(
            _event(
                "PyCon Latam 2030",
                "Regional Python conference with talks and workshops.",
                "Buenos Aires",
                30,
                100,
            ),
            EventStatus.PUBLISHED,
        )
        assert conference.id is not None
        for index, (title, speaker) in enumerate(
            [
                ("Opening keynote", speakers[0]),
                ("Inside the Linux kernel", speakers[1]),
                ("Writing software for the Moon", speakers[2]),
            ]
        ):
            start, end = _day(30, 9 + index * 2)
            assert speaker.id is not None
            sessions.create(admin, conference.id, SessionDetails(title, speaker.id, start, end, 50))

        almost_full = create(
            _event(
                "Clean Architecture Workshop",
                "Hands-on hexagonal architecture. Only one seat left.",
                "Montevideo",
                14,
                3,
            ),
            EventStatus.PUBLISHED,
        )
        full = create(
            _event(
                "Docker Bootcamp",
                "Sold out: try registering to see the capacity rule.",
                "Santiago",
                21,
                2,
            ),
            EventStatus.PUBLISHED,
        )
        create(
            _event(
                "Draft: Rust for Pythonistas",
                "Not published yet; only the admin sees it.",
                "Online",
                45,
                40,
            )
        )
        create(
            _event(
                "Cancelled: Legacy Meetup",
                "Cancelled event, for the status filter.",
                "Lima",
                10,
                30,
            ),
            EventStatus.CANCELLED,
        )

        assert almost_full.id is not None and full.id is not None
        for attendee in attendees[1:3]:
            registrations.register(attendee, almost_full.id)
        for attendee in attendees[1:3]:
            registrations.register(attendee, full.id)

    print("Demo data loaded.")
    print(f"admin:     {admin_email} (password from ADMIN_PASSWORD)")
    print(f"attendee:  {', '.join(ATTENDEE_EMAILS)} (password: {ATTENDEE_PASSWORD})")
    print("organizer: register a new account in the app; new accounts are organizers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
