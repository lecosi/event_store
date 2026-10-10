from app.application.errors import EmailAlreadyRegisteredError, InvalidTokenError
from app.domain.enums import EventStatus, Role
from app.domain.event import Event, EventFilters
from app.domain.user import UserAccount


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[int, UserAccount] = {}

    def get_by_id(self, user_id: int) -> UserAccount | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> UserAccount | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def add(self, email: str, password_hash: str, role: Role) -> UserAccount:
        if self.get_by_email(email):
            raise EmailAlreadyRegisteredError(email)
        user = UserAccount(
            email=email, password_hash=password_hash, role=role, id=len(self._by_id) + 1
        )
        self._by_id[user.id] = user
        return user


class FakeEventRepository:
    def __init__(self) -> None:
        self._events: dict[int, Event] = {}
        self._next_id = 1

    def add(self, event: Event) -> Event:
        event.id = self._next_id
        self._next_id += 1
        self._events[event.id] = event
        return event

    def get(self, event_id: int) -> Event | None:
        return self._events.get(event_id)

    def list_page(self, filters: EventFilters, page: int, size: int) -> tuple[list[Event], int]:
        matching = [e for e in self._events.values() if self._matches(e, filters)]
        matching.sort(key=lambda e: e.start_at)
        start = (page - 1) * size
        return matching[start : start + size], len(matching)

    @staticmethod
    def _matches(event: Event, filters: EventFilters) -> bool:
        if not filters.unrestricted and not (
            event.status is EventStatus.PUBLISHED or event.organizer_id == filters.viewer_id
        ):
            return False
        if filters.status is not None and event.status is not filters.status:
            return False
        return not filters.q or filters.q.lower() in event.name.lower()

    def update(self, event: Event) -> Event:
        assert event.id is not None
        self._events[event.id] = event
        return event

    def delete(self, event_id: int) -> None:
        self._events.pop(event_id, None)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{password}"


class FakeTokenService:
    def create_access_token(self, user_id: int) -> str:
        return f"token-{user_id}"

    def read_subject(self, token: str) -> int:
        if not token.startswith("token-"):
            raise InvalidTokenError
        return int(token.removeprefix("token-"))
