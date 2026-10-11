from sqlmodel import Session


class SqlUnitOfWork:
    """UnitOfWork port backed by the session shared with the request's repositories."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
