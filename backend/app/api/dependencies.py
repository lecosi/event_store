"""Shared FastAPI dependencies: wiring of concrete adapters and authorization guards."""

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.application.auth_service import AuthService, UserAdminService
from app.application.cache_policy import EventCache, SessionCache, SpeakerCache
from app.application.clock import Clock, utc_now
from app.application.errors import InvalidTokenError
from app.application.event_service import EventService
from app.application.guards import EventAccessPolicy
from app.application.ports import (
    Cache,
    EventAccess,
    EventRepository,
    EventUsageQueries,
    PasswordHasher,
    RegistrationRepository,
    SessionAvailabilityReader,
    SessionEnrollmentLock,
    SessionEnrollmentWriter,
    SessionParticipantQueries,
    SessionRepository,
    SpeakerRepository,
    SpeakerUsageQueries,
    TokenService,
    UnitOfWork,
    UserRepository,
)
from app.application.readers import EventCatalogue, EventSchedule, SpeakerDirectory
from app.application.registration_service import RegistrationService
from app.application.report_service import ReportService, SessionReportService
from app.application.session_catalogue import SessionCatalogue
from app.application.session_registration_service import SessionRegistrationService
from app.application.session_service import SessionService
from app.application.speaker_service import SpeakerService
from app.core.config import Settings, get_settings
from app.domain.enums import Role
from app.domain.roles import ORGANIZING_ROLES
from app.domain.user import UserAccount
from app.infrastructure.cache.cached_readers import (
    CachedEventCatalogue,
    CachedEventSchedule,
    CachedSpeakerDirectory,
)
from app.infrastructure.cache.null_cache import NullCache
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.registration_repository import SqlRegistrationRepository
from app.infrastructure.db.session import get_session
from app.infrastructure.db.session_registration_repository import (
    SqlSessionRegistrationRepository,
)
from app.infrastructure.db.session_repository import SqlSessionRepository
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.db.usage_queries import SqlEventUsageQueries, SqlSpeakerUsageQueries
from app.infrastructure.db.user_repository import SqlUserRepository
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.security.password_hasher import Argon2PasswordHasher

bearer_scheme = HTTPBearer(auto_error=False)


def get_clock() -> Clock:
    return utc_now


def get_unit_of_work(session: Session = Depends(get_session)) -> UnitOfWork:
    return SqlUnitOfWork(session)


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlUserRepository(session)


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache(maxsize=4)
def _build_cache(redis_url: str | None) -> Cache:
    return RedisCache.from_url(redis_url) if redis_url else NullCache()


def get_cache(settings: Settings = Depends(get_settings)) -> Cache:
    return _build_cache(settings.redis_url)


def get_token_service(settings: Settings = Depends(get_settings)) -> TokenService:
    return JwtTokenService(
        settings.jwt_secret,
        settings.jwt_algorithm,
        settings.access_token_expire_minutes,
        clock=utc_now,
    )


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenService = Depends(get_token_service),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> AuthService:
    return AuthService(users, hasher, tokens, uow)


def get_user_admin_service(
    users: UserRepository = Depends(get_user_repository),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> UserAdminService:
    return UserAdminService(users, uow)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> UserAccount:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        return auth.authenticate(credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized from exc


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> UserAccount | None:
    """Resolve the caller when a valid token is sent; anonymous otherwise (never raises)."""
    if credentials is None:
        return None
    try:
        return auth.authenticate(credentials.credentials)
    except InvalidTokenError:
        return None


def get_event_repository(session: Session = Depends(get_session)) -> EventRepository:
    return SqlEventRepository(session)


def get_event_usage_queries(session: Session = Depends(get_session)) -> EventUsageQueries:
    return SqlEventUsageQueries(session)


def get_event_cache(
    cache: Cache = Depends(get_cache), settings: Settings = Depends(get_settings)
) -> EventCache:
    return EventCache(cache, settings.cache_ttl_events_seconds)


def get_session_cache(
    cache: Cache = Depends(get_cache), settings: Settings = Depends(get_settings)
) -> SessionCache:
    return SessionCache(cache, settings.cache_ttl_sessions_seconds)


def get_speaker_cache(
    cache: Cache = Depends(get_cache), settings: Settings = Depends(get_settings)
) -> SpeakerCache:
    return SpeakerCache(cache, settings.cache_ttl_speakers_seconds)


def get_event_service(
    events: EventRepository = Depends(get_event_repository),
    usage: EventUsageQueries = Depends(get_event_usage_queries),
    uow: UnitOfWork = Depends(get_unit_of_work),
    cache: EventCache = Depends(get_event_cache),
) -> EventService:
    return EventService(events, usage, uow, cache)


def get_event_catalogue(
    service: EventService = Depends(get_event_service),
    cache: EventCache = Depends(get_event_cache),
) -> EventCatalogue:
    return CachedEventCatalogue(service, cache)


def get_speaker_repository(session: Session = Depends(get_session)) -> SpeakerRepository:
    return SqlSpeakerRepository(session)


def get_speaker_usage_queries(session: Session = Depends(get_session)) -> SpeakerUsageQueries:
    return SqlSpeakerUsageQueries(session)


def get_session_repository(session: Session = Depends(get_session)) -> SessionRepository:
    return SqlSessionRepository(session)


def get_speaker_service(
    speakers: SpeakerRepository = Depends(get_speaker_repository),
    usage: SpeakerUsageQueries = Depends(get_speaker_usage_queries),
    uow: UnitOfWork = Depends(get_unit_of_work),
    cache: SpeakerCache = Depends(get_speaker_cache),
) -> SpeakerService:
    return SpeakerService(speakers, usage, uow, cache)


def get_speaker_directory(
    service: SpeakerService = Depends(get_speaker_service),
    cache: SpeakerCache = Depends(get_speaker_cache),
) -> SpeakerDirectory:
    return CachedSpeakerDirectory(service, cache)


def get_session_registration_repository(
    session: Session = Depends(get_session),
) -> SqlSessionRegistrationRepository:
    return SqlSessionRegistrationRepository(session)


def get_enrollment_lock(
    enrollments: SqlSessionRegistrationRepository = Depends(get_session_registration_repository),
) -> SessionEnrollmentLock:
    return enrollments


def get_enrollment_writer(
    enrollments: SqlSessionRegistrationRepository = Depends(get_session_registration_repository),
) -> SessionEnrollmentWriter:
    return enrollments


def get_availability_reader(
    enrollments: SqlSessionRegistrationRepository = Depends(get_session_registration_repository),
) -> SessionAvailabilityReader:
    return enrollments


def get_session_participant_queries(
    enrollments: SqlSessionRegistrationRepository = Depends(get_session_registration_repository),
) -> SessionParticipantQueries:
    return enrollments


def get_session_service(
    events: EventRepository = Depends(get_event_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    speakers: SpeakerRepository = Depends(get_speaker_repository),
    enrollment_lock: SessionEnrollmentLock = Depends(get_enrollment_lock),
    uow: UnitOfWork = Depends(get_unit_of_work),
    cache: SessionCache = Depends(get_session_cache),
) -> SessionService:
    return SessionService(events, sessions, speakers, enrollment_lock, uow, cache)


def get_event_schedule(
    service: SessionService = Depends(get_session_service),
    cache: SessionCache = Depends(get_session_cache),
) -> EventSchedule:
    return CachedEventSchedule(service, cache)


def get_registration_repository(
    session: Session = Depends(get_session),
) -> RegistrationRepository:
    return SqlRegistrationRepository(session)


def get_registration_service(
    events: EventRepository = Depends(get_event_repository),
    usage: EventUsageQueries = Depends(get_event_usage_queries),
    registrations: RegistrationRepository = Depends(get_registration_repository),
    enrollments: SessionEnrollmentWriter = Depends(get_enrollment_writer),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> RegistrationService:
    return RegistrationService(events, usage, registrations, enrollments, uow)


def get_session_registration_service(
    events: EventRepository = Depends(get_event_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    enrollments: SessionEnrollmentWriter = Depends(get_enrollment_writer),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> SessionRegistrationService:
    return SessionRegistrationService(events, sessions, enrollments, uow)


def get_session_catalogue(
    events: EventService = Depends(get_event_service),
    schedule: EventSchedule = Depends(get_event_schedule),
    availability: SessionAvailabilityReader = Depends(get_availability_reader),
) -> SessionCatalogue:
    return SessionCatalogue(events, schedule, availability)


def get_event_access(events: EventRepository = Depends(get_event_repository)) -> EventAccess:
    return EventAccessPolicy(events)


def get_report_service(
    access: EventAccess = Depends(get_event_access),
    registrations: RegistrationRepository = Depends(get_registration_repository),
) -> ReportService:
    return ReportService(access, registrations)


def get_session_report_service(
    access: EventAccess = Depends(get_event_access),
    sessions: SessionRepository = Depends(get_session_repository),
    participants: SessionParticipantQueries = Depends(get_session_participant_queries),
) -> SessionReportService:
    return SessionReportService(access, sessions, participants)


def require_role(*roles: Role) -> Callable[[UserAccount], UserAccount]:
    """Build a dependency that only lets users with one of ``roles`` through."""

    def checker(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


organizer_or_admin = require_role(*ORGANIZING_ROLES)
require_admin = require_role(Role.ADMIN)
