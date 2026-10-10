from sqlalchemy import Engine, inspect


def test_migrations_create_all_tables(postgres_engine: Engine):
    tables = set(inspect(postgres_engine).get_table_names())
    assert {"users", "event", "speaker", "session", "registration"} <= tables


def test_registration_has_unique_user_event_constraint(postgres_engine: Engine):
    uniques = inspect(postgres_engine).get_unique_constraints("registration")
    assert any(set(u["column_names"]) == {"user_id", "event_id"} for u in uniques)


def test_speaker_email_has_unique_constraint(postgres_engine: Engine):
    uniques = inspect(postgres_engine).get_unique_constraints("speaker")
    assert any(u["column_names"] == ["email"] for u in uniques)


def test_event_and_session_have_capacity_and_date_check_constraints(postgres_engine: Engine):
    inspector = inspect(postgres_engine)
    for table in ("event", "session"):
        names = {check["name"] for check in inspector.get_check_constraints(table)}
        assert {f"ck_{table}_capacity_positive", f"ck_{table}_dates_order"} <= names
