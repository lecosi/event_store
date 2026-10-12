from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_speaker_directory, get_speaker_service, organizer_or_admin
from app.api.openapi_params import PageNumber, PageSize, SpeakerId
from app.api.openapi_responses import (
    ORGANIZER_OR_ADMIN,
    SPEAKER_NOT_FOUND,
    combine,
    conflict,
)
from app.api.speaker_schemas import SpeakerPageResponse, SpeakerRequest, SpeakerResponse
from app.application.readers import SpeakerDirectory
from app.application.speaker_service import SpeakerService
from app.domain.speaker import Speaker, SpeakerDetails
from app.domain.user import UserAccount

router = APIRouter(prefix="/speakers", tags=["speakers"])


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
    directory: SpeakerDirectory = Depends(get_speaker_directory),
) -> SpeakerPageResponse:
    """Paginated speakers ordered by name, optionally filtered by `q`. Public, no token required."""

    result = directory.list_page(q=q, page=page, size=size)
    return SpeakerPageResponse(
        items=[SpeakerResponse.model_validate(s, from_attributes=True) for s in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get(
    "/{speaker_id}",
    response_model=SpeakerResponse,
    summary="Get a speaker",
    responses=SPEAKER_NOT_FOUND,
)
def get_speaker(
    speaker_id: SpeakerId,
    directory: SpeakerDirectory = Depends(get_speaker_directory),
) -> SpeakerResponse:
    """Return one speaker. Public, no token required."""

    return SpeakerResponse.model_validate(directory.get(speaker_id), from_attributes=True)


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
