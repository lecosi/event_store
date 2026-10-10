"""Documented path and query parameter types shared by several routers."""

from typing import Annotated

from fastapi import Path, Query

EventId = Annotated[int, Path(description="Identifier of the event.", examples=[1])]
SessionId = Annotated[int, Path(description="Identifier of the session.", examples=[1])]
SpeakerId = Annotated[int, Path(description="Identifier of the speaker.", examples=[1])]
UserId = Annotated[int, Path(description="Identifier of the user account.", examples=[2])]

PageNumber = Annotated[int, Query(ge=1, description="1-based page number to return.", examples=[1])]
PageSize = Annotated[
    int,
    Query(ge=1, le=100, description="Number of items per page (1-100).", examples=[10]),
]
