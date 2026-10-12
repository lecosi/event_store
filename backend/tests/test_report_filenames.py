from datetime import UTC, datetime

from app.application.report_filenames import participants_filename, session_participants_filename


def clock() -> datetime:
    return datetime(2030, 5, 9, 23, 59, tzinfo=UTC)


def test_participants_filename_uses_the_event_id_when_given() -> None:
    assert participants_filename(7, clock) == "participantes_evento_7.csv"


def test_participants_filename_uses_the_injected_date_without_event() -> None:
    assert participants_filename(None, clock) == "participantes_20300509.csv"


def test_session_participants_filename_uses_the_session_id_when_given() -> None:
    assert session_participants_filename(3, clock) == "participantes_sesion_3.csv"


def test_session_participants_filename_uses_the_injected_date_without_session() -> None:
    assert session_participants_filename(None, clock) == "participantes_sesiones_20300509.csv"
