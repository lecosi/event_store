"""Query parameters of the report endpoints, parsed into the report services' filter objects."""

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from app.application.report_service import ParticipantParams, SessionParticipantParams
from app.domain.enums import EventStatus


def participant_params(
    event_id: Annotated[
        int | None,
        Query(
            description=(
                "Only participants of this event. Organizers can only use their own events "
                "(403 otherwise); an unknown event answers 404."
            ),
            examples=[1],
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Case-insensitive text to look for in the event name (participant names are "
                "not searched)."
            ),
            examples=["python"],
        ),
    ] = None,
    status_filter: Annotated[
        EventStatus | None,
        Query(
            alias="status",
            description="Only participants of events in this status.",
            examples=["published"],
        ),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(
            description=(
                "First day (inclusive, UTC) of the event start date range, as `YYYY-MM-DD`."
            ),
            examples=["2030-05-01"],
        ),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(
            description=(
                "Last day (inclusive, UTC, until 23:59:59.999999) of the event start date "
                "range, as `YYYY-MM-DD`. It must not be before `date_from` (422)."
            ),
            examples=["2030-05-31"],
        ),
    ] = None,
) -> ParticipantParams:
    return ParticipantParams(
        event_id=event_id, q=q, status=status_filter, date_from=date_from, date_to=date_to
    )


Filters = Annotated[ParticipantParams, Depends(participant_params)]


def session_participant_params(
    event_id: Annotated[
        int | None,
        Query(
            description=(
                "Only people enrolled in sessions of this event. Organizers can only use their "
                "own events (403 otherwise); an unknown event answers 404."
            ),
            examples=[1],
        ),
    ] = None,
    session_id: Annotated[
        int | None,
        Query(
            description=(
                "Only people enrolled in this session. Organizers can only use sessions of "
                "their own events (403 otherwise); an unknown session answers 404."
            ),
            examples=[1],
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description=(
                "Case-insensitive text to look for in the session title or the event name "
                "(participant names are not searched)."
            ),
            examples=["keynote"],
        ),
    ] = None,
    status_filter: Annotated[
        EventStatus | None,
        Query(
            alias="status",
            description="Only enrollments in sessions of events in this status.",
            examples=["published"],
        ),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(
            description=(
                "First day (inclusive, UTC) of the session start date range, as `YYYY-MM-DD`."
            ),
            examples=["2030-05-01"],
        ),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(
            description=(
                "Last day (inclusive, UTC, until 23:59:59.999999) of the session start date "
                "range, as `YYYY-MM-DD`. It must not be before `date_from` (422)."
            ),
            examples=["2030-05-31"],
        ),
    ] = None,
) -> SessionParticipantParams:
    return SessionParticipantParams(
        event_id=event_id,
        session_id=session_id,
        q=q,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


SessionFilters = Annotated[SessionParticipantParams, Depends(session_participant_params)]


ParticipantFilters = Annotated[ParticipantParams, Depends(participant_params)]
SessionParticipantFilters = Annotated[SessionParticipantParams, Depends(session_participant_params)]
