from sqlalchemy import inspect
from sqlmodel import SQLModel, create_engine

from app.infrastructure.db import models  # noqa: F401  (registers tables)


def test_models_create_all_tables_in_memory_sqlite():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "event", "speaker", "session", "registration"} <= tables


def test_registration_has_unique_user_event_constraint():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    uniques = inspect(engine).get_unique_constraints("registration")
    assert any(set(u["column_names"]) == {"user_id", "event_id"} for u in uniques)
