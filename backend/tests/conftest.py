import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-0123456789-0123456789")

from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from alembic import command

from app.infrastructure.db import models  # noqa: F401  (register tables)
from app.infrastructure.db.session import get_session
from app.main import create_app


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "postgres: needs a real PostgreSQL (set TEST_POSTGRES_URL); skipped by default"
    )


POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")
POSTGRES_POOL_SIZE = 12


def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def _truncate_all(engine: Engine) -> None:
    quote = engine.dialect.identifier_preparer.quote
    tables = ", ".join(quote(table.name) for table in SQLModel.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    if not POSTGRES_URL:
        pytest.skip("set TEST_POSTGRES_URL to run against PostgreSQL")
    alembic_config = Config("alembic.ini")
    alembic_config.attributes["database_url"] = POSTGRES_URL
    command.upgrade(alembic_config, "head")
    engine = create_engine(POSTGRES_URL, pool_size=POSTGRES_POOL_SIZE)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_postgres(postgres_engine: Engine) -> Iterator[Engine]:
    _truncate_all(postgres_engine)
    yield postgres_engine
    _truncate_all(postgres_engine)


@pytest.fixture
def session(request: pytest.FixtureRequest) -> Iterator[Session]:
    if POSTGRES_URL:
        engine = request.getfixturevalue("clean_postgres")
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
