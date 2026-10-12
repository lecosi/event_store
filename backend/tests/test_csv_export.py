from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.api.csv_export import participants_csv, session_participants_csv
from app.domain.registration import ParticipantRow
from app.domain.session_registration import SessionParticipantRow

BOM = "﻿"
HEADER = "Nombre completo;Correo electrónico;Evento\r\n"


def render(*rows: ParticipantRow) -> str:
    return "".join(participants_csv(iter(rows)))


def test_empty_export_is_only_the_bom_and_the_header() -> None:
    assert render() == BOM + HEADER


def test_rows_use_semicolons_and_crlf() -> None:
    body = render(ParticipantRow("Ana Gómez", "ana@example.com", "PyCon"))

    assert body == BOM + HEADER + "Ana Gómez;ana@example.com;PyCon\r\n"


def test_values_with_separator_or_quotes_are_quoted() -> None:
    body = render(ParticipantRow('Ana "La Jefa"', "ana@example.com", "Charlas; talleres"))

    assert body.endswith('"Ana ""La Jefa""";ana@example.com;"Charlas; talleres"\r\n')


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_cells_starting_with_a_formula_character_are_neutralized(prefix: str) -> None:
    dangerous = f"{prefix}HYPERLINK(1)"

    body = render(ParticipantRow(dangerous, "a@example.com", "PyCon"))

    cells = body.removeprefix(BOM + HEADER)
    assert cells.lstrip('"').startswith(f"'{dangerous}")


def test_every_column_is_neutralized() -> None:
    body = render(ParticipantRow("=A", "+b@example.com", "@Evento"))

    assert body.endswith("'=A;'+b@example.com;'@Evento\r\n")


def test_safe_values_are_left_untouched() -> None:
    body = render(ParticipantRow("A-B", "a@b.co", "Evento 2+2"))

    assert body.endswith("A-B;a@b.co;Evento 2+2\r\n")


def test_export_is_lazy() -> None:
    consumed: list[int] = []

    def rows():
        for n in range(3):
            consumed.append(n)
            yield ParticipantRow(f"P{n}", "p@example.com", "E")

    chunks = participants_csv(rows())
    next(chunks)
    next(chunks)

    assert consumed == [0]


def render_sessions(*rows: SessionParticipantRow) -> str:
    return "".join(session_participants_csv(iter(rows)))


SESSION_HEADER = "Nombre completo;Correo electrónico;Evento;Sesión;Inicio de la sesión\r\n"
START = datetime(2030, 3, 10, 9, tzinfo=UTC)


def test_empty_session_export_is_only_the_bom_and_the_header() -> None:
    assert render_sessions() == BOM + SESSION_HEADER


def test_session_rows_include_title_and_start_in_utc() -> None:
    body = render_sessions(
        SessionParticipantRow("Ana", "ana@example.com", "PyCon", "Keynote", START)
    )

    assert (
        body == BOM + SESSION_HEADER + "Ana;ana@example.com;PyCon;Keynote;2030-03-10T09:00:00Z\r\n"
    )


def test_session_start_is_converted_to_utc() -> None:
    lima = START.astimezone(timezone(timedelta(hours=-5)))

    body = render_sessions(
        SessionParticipantRow("Ana", "ana@example.com", "PyCon", "Keynote", lima)
    )

    assert body.endswith(";2030-03-10T09:00:00Z\r\n")


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_session_title_starting_with_a_formula_character_is_neutralized(prefix: str) -> None:
    dangerous = f"{prefix}HYPERLINK(1)"

    body = render_sessions(SessionParticipantRow("Ana", "a@example.com", "PyCon", dangerous, START))

    cells = body.removeprefix(BOM + SESSION_HEADER)
    assert f"'{dangerous}" in cells
