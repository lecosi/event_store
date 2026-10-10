"""Documented path and query parameter types shared by several routers."""

from typing import Annotated

from fastapi import Path, Query

EventId = Annotated[int, Path(description="Identifier of the event.", examples=[1])]

PageNumber = Annotated[int, Query(ge=1, description="1-based page number to return.", examples=[1])]
PageSize = Annotated[
    int,
    Query(ge=1, le=100, description="Number of items per page (1-100).", examples=[10]),
]
