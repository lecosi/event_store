"""Speaker use cases. Depend only on ports and pure domain rules."""

from app.application.errors import (
    PermissionDeniedError,
    SpeakerEmailTakenError,
    SpeakerInUseError,
    SpeakerNotFoundError,
)
from app.application.ports import (
    SESSIONS_NAMESPACE,
    SPEAKERS_NAMESPACE,
    Cache,
    NullCache,
    SpeakerRepository,
    UnitOfWork,
    transaction,
)
from app.domain.enums import Role
from app.domain.speaker import Speaker, SpeakerDetails, SpeakerPage
from app.domain.user import UserAccount

MANAGING_ROLES = (Role.ORGANIZER, Role.ADMIN)


def _normalize(details: SpeakerDetails) -> SpeakerDetails:
    email = details.email.strip().lower() if details.email else None
    return SpeakerDetails(name=details.name.strip(), bio=details.bio, email=email or None)


class SpeakerService:
    def __init__(
        self, speakers: SpeakerRepository, uow: UnitOfWork, cache: Cache | None = None
    ) -> None:
        self._speakers = speakers
        self._uow = uow
        self._cache: Cache = cache if cache is not None else NullCache()

    def create(self, actor: UserAccount, details: SpeakerDetails) -> Speaker:
        with transaction(self._uow):
            self._require_manager(actor)
            details = _normalize(details)
            self._ensure_email_free(details.email, speaker_id=None)
            created = self._speakers.add(
                Speaker(name=details.name, bio=details.bio, email=details.email)
            )
        self._cache.invalidate(SPEAKERS_NAMESPACE)
        return created

    def get(self, speaker_id: int) -> Speaker:
        speaker = self._speakers.get(speaker_id)
        if speaker is None:
            raise SpeakerNotFoundError(speaker_id)
        return speaker

    def list_page(self, q: str | None = None, page: int = 1, size: int = 10) -> SpeakerPage:
        term = q.strip() if q else None
        items, total = self._speakers.list_page(term or None, page, size)
        return SpeakerPage(items=items, total=total, page=page, size=size)

    def update(self, actor: UserAccount, speaker_id: int, details: SpeakerDetails) -> Speaker:
        with transaction(self._uow):
            self._require_manager(actor)
            speaker = self.get(speaker_id)
            details = _normalize(details)
            self._ensure_email_free(details.email, speaker_id=speaker_id)
            updated = self._speakers.update(speaker.with_details(details))
        self._invalidate_speaker_and_sessions()
        return updated

    def delete(self, actor: UserAccount, speaker_id: int) -> None:
        with transaction(self._uow):
            self._require_manager(actor)
            self.get(speaker_id)
            if self._speakers.count_sessions(speaker_id) > 0:
                raise SpeakerInUseError(speaker_id)
            self._speakers.delete(speaker_id)
        self._invalidate_speaker_and_sessions()

    def _invalidate_speaker_and_sessions(self) -> None:
        self._cache.invalidate(SPEAKERS_NAMESPACE)
        self._cache.invalidate(SESSIONS_NAMESPACE)

    def _ensure_email_free(self, email: str | None, speaker_id: int | None) -> None:
        if email is None:
            return
        existing = self._speakers.get_by_email(email)
        if existing is not None and existing.id != speaker_id:
            raise SpeakerEmailTakenError(email)

    @staticmethod
    def _require_manager(actor: UserAccount) -> None:
        if actor.role not in MANAGING_ROLES:
            raise PermissionDeniedError
