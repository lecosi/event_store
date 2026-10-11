from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from alembic.config import Config

SCRATCH_DATABASE = "full_name_migration_test"
PREVIOUS_REVISION = "0003"


def _config(url: str) -> Config:
    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    return config


@pytest.fixture
def scratch_engine(postgres_engine: Engine) -> Iterator[Engine]:
    maintenance = create_engine(
        postgres_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with maintenance.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DATABASE} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {SCRATCH_DATABASE}"))
    engine = create_engine(postgres_engine.url.set(database=SCRATCH_DATABASE))
    yield engine
    engine.dispose()
    with maintenance.connect() as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DATABASE} WITH (FORCE)"))
    maintenance.dispose()


def _insert_user(engine: Engine, email: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (email, password_hash, role, is_active) "
                "VALUES (:email, 'h', 'ATTENDEE', true)"
            ),
            {"email": email},
        )


def _full_names(engine: Engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT email, full_name FROM users")).all()
    return {email: name for email, name in rows}


def test_upgrade_backfills_existing_users_from_the_email_local_part(
    scratch_engine: Engine,
) -> None:
    config = _config(scratch_engine.url.render_as_string(hide_password=False))
    command.upgrade(config, PREVIOUS_REVISION)
    _insert_user(scratch_engine, "ana.perez@example.com")
    _insert_user(scratch_engine, "luis@example.org")

    command.upgrade(config, "head")

    assert _full_names(scratch_engine) == {
        "ana.perez@example.com": "ana.perez",
        "luis@example.org": "luis",
    }


def test_upgrade_makes_full_name_required_without_a_default(scratch_engine: Engine) -> None:
    config = _config(scratch_engine.url.render_as_string(hide_password=False))
    command.upgrade(config, "head")

    column = next(
        c for c in inspect(scratch_engine).get_columns("users") if c["name"] == "full_name"
    )
    assert column["nullable"] is False
    assert column["default"] is None
    with pytest.raises(IntegrityError):
        _insert_user(scratch_engine, "ana@example.com")


def test_downgrade_drops_the_column_and_upgrade_restores_it(scratch_engine: Engine) -> None:
    config = _config(scratch_engine.url.render_as_string(hide_password=False))
    command.upgrade(config, PREVIOUS_REVISION)
    _insert_user(scratch_engine, "ana@example.com")
    command.upgrade(config, "head")

    command.downgrade(config, PREVIOUS_REVISION)
    columns = {c["name"] for c in inspect(scratch_engine).get_columns("users")}
    assert "full_name" not in columns

    command.upgrade(config, "head")
    assert _full_names(scratch_engine) == {"ana@example.com": "ana"}
