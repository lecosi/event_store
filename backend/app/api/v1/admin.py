from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_user_admin_service, require_role
from app.api.error_handlers import SELF_LOCKOUT_DETAIL
from app.api.openapi_params import PageNumber, PageSize, UserId
from app.api.openapi_responses import ORGANIZER_OR_ADMIN, USER_NOT_FOUND, combine, conflict
from app.api.schemas import UserResponse
from app.application.auth_service import UserAdminService
from app.domain.enums import Role
from app.domain.user import UserAccount

require_admin = require_role(Role.ADMIN)


class UserPageResponse(BaseModel):
    """One page of user accounts."""

    items: list[UserResponse] = Field(description="Users on this page, ordered by id.")
    total: int = Field(description="Total user accounts across all pages.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])


class UserAdminUpdate(BaseModel):
    """Fields an admin may change; omitted fields stay untouched."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"role": "organizer"}]})

    role: Role | None = Field(
        default=None, description="New role for the user.", examples=["organizer"]
    )
    is_active: bool | None = Field(
        default=None, description="Activate (`true`) or deactivate (`false`) the account."
    )


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses=ORGANIZER_OR_ADMIN,
)


@router.get("/users", response_model=UserPageResponse, summary="List users")
def list_users(
    page: PageNumber = 1,
    size: PageSize = 10,
    service: UserAdminService = Depends(get_user_admin_service),
) -> UserPageResponse:
    """Paginated list of user accounts, ordered by id. Admin only."""
    result = service.list_users(page=page, size=size)
    return UserPageResponse(
        items=[UserResponse.model_validate(u, from_attributes=True) for u in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Change a user's role or active flag",
    responses=combine(
        USER_NOT_FOUND,
        conflict(
            "An admin cannot demote or deactivate their own account.",
            SELF_LOCKOUT_DETAIL,
        ),
    ),
)
def update_user(
    user_id: UserId,
    body: UserAdminUpdate,
    actor: UserAccount = Depends(require_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> UserAccount:
    """Partially update a user. Admin only.

    Send only the fields to change: `role` (`admin`, `organizer`, `attendee`) and/or
    `is_active`. Deactivating an account blocks its login and any token already issued.

    An admin cannot change their own role away from `admin` nor deactivate themselves (409);
    another admin has to do it.
    """
    return service.update_user(actor, user_id, role=body.role, is_active=body.is_active)
