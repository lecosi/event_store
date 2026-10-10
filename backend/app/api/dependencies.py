"""Shared FastAPI dependencies: wiring of concrete adapters and authorization guards."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.application.auth_service import AuthService
from app.application.errors import InvalidTokenError
from app.application.event_service import EventService
from app.application.ports import (
    EventRepository,
    PasswordHasher,
    SessionRepository,
    SpeakerRepository,
    TokenService,
    UserRepository,
)
from app.application.session_service import SessionService
from app.application.speaker_service import SpeakerService
from app.core.config import Settings, get_settings
from app.domain.enums import Role
from app.domain.user import UserAccount
from app.infrastructure.db.event_repository import SqlEventRepository
from app.infrastructure.db.session import get_session
from app.infrastructure.db.session_repository import SqlSessionRepository
from app.infrastructure.db.speaker_repository import SqlSpeakerRepository
from app.infrastructure.db.user_repository import SqlUserRepository
from app.infrastructure.security.jwt_tokens import JwtTokenService
from app.infrastructure.security.password_hasher import Argon2PasswordHasher

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return SqlUserRepository(session)


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_token_service(settings: Settings = Depends(get_settings)) -> TokenService:
    return JwtTokenService(
        settings.jwt_secret, settings.jwt_algorithm, settings.access_token_expire_minutes
    )


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenService = Depends(get_token_service),
) -> AuthService:
    return AuthService(users, hasher, tokens)


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


def get_event_service(events: EventRepository = Depends(get_event_repository)) -> EventService:
    return EventService(events)


def get_speaker_repository(session: Session = Depends(get_session)) -> SpeakerRepository:
    return SqlSpeakerRepository(session)


def get_session_repository(session: Session = Depends(get_session)) -> SessionRepository:
    return SqlSessionRepository(session)


def get_speaker_service(
    speakers: SpeakerRepository = Depends(get_speaker_repository),
) -> SpeakerService:
    return SpeakerService(speakers)


def get_session_service(
    events: EventRepository = Depends(get_event_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    speakers: SpeakerRepository = Depends(get_speaker_repository),
) -> SessionService:
    return SessionService(events, sessions, speakers)


def require_role(*roles: Role) -> Callable[[UserAccount], UserAccount]:
    """Build a dependency that only lets users with one of ``roles`` through."""

    def checker(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
