import os

os.environ.setdefault("JWT_SECRET", "test-only-secret-0123456789-0123456789")

from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from alembic import command

from app.core.config import get_settings
from app.infrastructure.db import models  # noqa: F401  (register tables)
from app.infrastructure.db.session import get_session
from app.main import create_app

TEST_DATABASE_SUFFIX = "_test"
MAINTENANCE_DATABASE = "postgres"
POOL_SIZE = 12


def _resolve_test_database_url() -> URL:
    explicit_url = os.environ.get("TEST_DATABASE_URL")
    if explicit_url:
        url = make_url(explicit_url)
    else:
        configured = make_url(get_settings().database_url)
        url = configured.set(database=f"{configured.database}{TEST_DATABASE_SUFFIX}")
    if not (url.database or "").endswith(TEST_DATABASE_SUFFIX):
        raise pytest.UsageError(
            f"Test database name must end with '{TEST_DATABASE_SUFFIX}' to avoid truncating "
            f"a real database (got '{url.database}')."
        )
    return url


def _create_database_if_missing(url: URL) -> None:
    maintenance_engine = create_engine(
        url.set(database=MAINTENANCE_DATABASE), isolation_level="AUTOCOMMIT"
    )
    try:
        with maintenance_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                quoted_name = maintenance_engine.dialect.identifier_preparer.quote(url.database)
                connection.execute(text(f"CREATE DATABASE {quoted_name}"))
    finally:
        maintenance_engine.dispose()


def _migrate_to_head(url: URL) -> None:
    alembic_config = Config("alembic.ini")
    alembic_config.attributes["database_url"] = url.render_as_string(hide_password=False)
    command.upgrade(alembic_config, "head")


def _truncate_all_tables(engine: Engine) -> None:
    quote = engine.dialect.identifier_preparer.quote
    tables = ", ".join(quote(table.name) for table in SQLModel.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    url = _resolve_test_database_url()
    try:
        _create_database_if_missing(url)
    except OperationalError as error:
        pytest.exit(
            f"PostgreSQL is not reachable at {url.render_as_string()}; start it or set "
            f"TEST_DATABASE_URL.\n{error.orig}",
            returncode=2,
        )
    _migrate_to_head(url)
    engine = create_engine(url, pool_size=POOL_SIZE)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_postgres(postgres_engine: Engine) -> Iterator[Engine]:
    _truncate_all_tables(postgres_engine)
    yield postgres_engine
    _truncate_all_tables(postgres_engine)


@pytest.fixture
def session(clean_postgres: Engine) -> Iterator[Session]:
    with Session(clean_postgres) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


POSTGRES_FIXTURES = frozenset({"postgres_engine", "clean_postgres", "session", "client"})


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        fixtures = getattr(item, "fixturenames", ())
        needs_database = POSTGRES_FIXTURES.intersection(fixtures)
        item.add_marker(pytest.mark.integration if needs_database else pytest.mark.unit)
