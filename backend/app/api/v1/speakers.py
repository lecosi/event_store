from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import TypeAdapter

from app.api.cached_reads import read_through, text_digest
from app.api.dependencies import get_cache, get_speaker_service, require_role
from app.api.openapi_params import PageNumber, PageSize, SpeakerId
from app.api.openapi_responses import (
    ORGANIZER_OR_ADMIN,
    SPEAKER_NOT_FOUND,
    combine,
    conflict,
)
from app.api.speaker_schemas import SpeakerPageResponse, SpeakerRequest, SpeakerResponse
from app.application.ports import SPEAKERS_NAMESPACE, Cache
from app.application.speaker_service import SpeakerService
from app.core.config import Settings, get_settings
from app.domain.enums import Role
from app.domain.speaker import Speaker, SpeakerDetails
from app.domain.user import UserAccount

router = APIRouter(prefix="/speakers", tags=["speakers"])

organizer_or_admin = require_role(Role.ORGANIZER, Role.ADMIN)

SPEAKER_PAGE = TypeAdapter(SpeakerPageResponse)
SPEAKER = TypeAdapter(SpeakerResponse)


def _details(body: SpeakerRequest) -> SpeakerDetails:
    return SpeakerDetails(name=body.name, bio=body.bio, email=body.email)


EMAIL_TAKEN = conflict("Another speaker already uses that email.", "Speaker email already in use")


@router.post(
    "",
    response_model=SpeakerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a speaker",
    responses=combine(ORGANIZER_OR_ADMIN, EMAIL_TAKEN),
)
def create_speaker(
    body: SpeakerRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: SpeakerService = Depends(get_speaker_service),
) -> Speaker:
    """Add a speaker to the shared directory. Requires `organizer` or `admin`.

    The optional email must be unique among speakers (409 otherwise).
    """
    return service.create(user, _details(body))


@router.get("", response_model=SpeakerPageResponse, summary="List speakers")
def list_speakers(
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Case-insensitive substring search on the speaker name.",
            examples=["grace"],
        ),
    ] = None,
    page: PageNumber = 1,
    size: PageSize = 10,
    service: SpeakerService = Depends(get_speaker_service),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> SpeakerPageResponse:
    """Paginated speakers ordered by name, optionally filtered by `q`. Public, no token required."""

    def build() -> SpeakerPageResponse:
        result = service.list_page(q=q, page=page, size=size)
        return SpeakerPageResponse(
            items=[SpeakerResponse.model_validate(s, from_attributes=True) for s in result.items],
            total=result.total,
            page=result.page,
            size=result.size,
            pages=result.pages,
        )

    key = f"list:{text_digest(q)}:{page}:{size}"
    ttl = settings.cache_ttl_speakers_seconds
    return read_through(cache, SPEAKERS_NAMESPACE, key, ttl, SPEAKER_PAGE, build)


@router.get(
    "/{speaker_id}",
    response_model=SpeakerResponse,
    summary="Get a speaker",
    responses=SPEAKER_NOT_FOUND,
)
def get_speaker(
    speaker_id: SpeakerId,
    service: SpeakerService = Depends(get_speaker_service),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> SpeakerResponse:
    """Return one speaker. Public, no token required."""

    def build() -> SpeakerResponse:
        return SpeakerResponse.model_validate(service.get(speaker_id), from_attributes=True)

    ttl = settings.cache_ttl_speakers_seconds
    return read_through(cache, SPEAKERS_NAMESPACE, f"detail:{speaker_id}", ttl, SPEAKER, build)


@router.put(
    "/{speaker_id}",
    response_model=SpeakerResponse,
    summary="Update a speaker",
    responses=combine(ORGANIZER_OR_ADMIN, SPEAKER_NOT_FOUND, EMAIL_TAKEN),
)
def update_speaker(
    speaker_id: SpeakerId,
    body: SpeakerRequest,
    user: UserAccount = Depends(organizer_or_admin),
    service: SpeakerService = Depends(get_speaker_service),
) -> Speaker:
    """Replace a speaker's data. Requires `organizer` or `admin`.

    The email must stay unique among speakers (409 otherwise).
    """
    return service.update(user, speaker_id, _details(body))


@router.delete(
    "/{speaker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a speaker",
    responses=combine(
        ORGANIZER_OR_ADMIN,
        SPEAKER_NOT_FOUND,
        conflict("The speaker still has sessions.", "Speaker has sessions and cannot be deleted"),
    ),
)
def delete_speaker(
    speaker_id: SpeakerId,
    user: UserAccount = Depends(organizer_or_admin),
    service: SpeakerService = Depends(get_speaker_service),
) -> Response:
    """Delete a speaker. Requires `organizer` or `admin`.

    A speaker that still has sessions cannot be deleted (409); remove those sessions first.
    """
    service.delete(user, speaker_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
