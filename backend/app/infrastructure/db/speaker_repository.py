from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.application.errors import SpeakerEmailTakenError
from app.domain.speaker import Speaker
from app.infrastructure.db.event_repository import LIKE_ESCAPE, escape_like
from app.infrastructure.db.models import Session as SessionRow
from app.infrastructure.db.models import Speaker as SpeakerRow


def _to_domain(row: SpeakerRow) -> Speaker:
    return Speaker(id=row.id, name=row.name, bio=row.bio, email=row.email)


class SqlSpeakerRepository:
    """SQLModel implementation of the SpeakerRepository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, speaker: Speaker) -> Speaker:
        row = SpeakerRow(name=speaker.name, bio=speaker.bio, email=speaker.email)
        self._session.add(row)
        self._commit(speaker.email)
        self._session.refresh(row)
        return _to_domain(row)

    def get(self, speaker_id: int) -> Speaker | None:
        row = self._session.get(SpeakerRow, speaker_id)
        return _to_domain(row) if row else None

    def get_by_email(self, email: str) -> Speaker | None:
        row = self._session.exec(select(SpeakerRow).where(SpeakerRow.email == email)).first()
        return _to_domain(row) if row else None

    def list_page(self, q: str | None, page: int, size: int) -> tuple[list[Speaker], int]:
        query = select(SpeakerRow)
        count = select(func.count()).select_from(SpeakerRow)
        if q:
            # Bound parameter + escaped wildcards: never build SQL from user input.
            condition = col(SpeakerRow.name).ilike(f"%{escape_like(q)}%", escape=LIKE_ESCAPE)
            query = query.where(condition)
            count = count.where(condition)
        total = self._session.exec(count).one()
        rows = self._session.exec(
            query.order_by(col(SpeakerRow.name), col(SpeakerRow.id))
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return [_to_domain(row) for row in rows], total

    def update(self, speaker: Speaker) -> Speaker:
        row = self._session.get(SpeakerRow, speaker.id)
        if row is None:
            raise LookupError(f"Speaker {speaker.id} does not exist")
        row.name = speaker.name
        row.bio = speaker.bio
        row.email = speaker.email
        self._session.add(row)
        self._commit(speaker.email)
        self._session.refresh(row)
        return _to_domain(row)

    def _commit(self, email: str | None) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise SpeakerEmailTakenError(email or "") from exc

    def delete(self, speaker_id: int) -> None:
        row = self._session.get(SpeakerRow, speaker_id)
        if row is not None:
            self._session.delete(row)
            self._session.commit()

    def count_sessions(self, speaker_id: int) -> int:
        return self._session.exec(
            select(func.count())
            .select_from(SessionRow)
            .where(col(SessionRow.speaker_id) == speaker_id)
        ).one()
