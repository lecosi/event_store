from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.api.dependencies import get_user_admin_service, require_admin
from app.api.error_handlers import EMAIL_TAKEN_DETAIL, SELF_LOCKOUT_DETAIL
from app.api.openapi_params import PageNumber, PageSize, UserId
from app.api.openapi_responses import (
    ORGANIZER_OR_ADMIN,
    USER_NOT_FOUND,
    combine,
    conflicts,
    validation_error,
)
from app.api.schemas import FullName, UserResponse
from app.application.auth_service import UserAdminService
from app.domain.enums import Role
from app.domain.user import MAX_FULL_NAME_LENGTH, UserAccount


class UserPageResponse(BaseModel):
    """One page of user accounts."""

    items: list[UserResponse] = Field(description="Users on this page, ordered by id.")
    total: int = Field(description="Total user accounts across all pages.", examples=[25])
    page: int = Field(description="Current 1-based page number.", examples=[1])
    size: int = Field(description="Requested page size.", examples=[10])
    pages: int = Field(description="Total number of pages (0 when empty).", examples=[3])


class UserAdminUpdate(BaseModel):
    """Fields an admin may change; omitted fields stay untouched. At least one is required."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"full_name": "Ana Maria Perez"},
                {"email": "ana.perez@example.com"},
                {
                    "full_name": "Ana Maria Perez",
                    "email": "ana.perez@example.com",
                    "role": "organizer",
                },
                {"is_active": False},
            ]
        }
    )

    full_name: FullName | None = Field(
        default=None,
        description=(
            "New full name. Surrounding whitespace is trimmed; "
            f"1 to {MAX_FULL_NAME_LENGTH} characters."
        ),
        examples=["Ana Maria Perez"],
    )
    email: EmailStr | None = Field(
        default=None,
        description=(
            "New email address, also the login name. Stored trimmed and in lowercase; "
            "it must not belong to another user. Tokens already issued stay valid."
        ),
        examples=["ana.perez@example.com"],
    )
    role: Role | None = Field(
        default=None, description="New role for the user.", examples=["organizer"]
    )
    is_active: bool | None = Field(
        default=None, description="Activate (`true`) or deactivate (`false`) the account."
    )

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UserAdminUpdate":
        if all(value is None for value in (self.full_name, self.email, self.role, self.is_active)):
            raise ValueError("Send at least one of full_name, email, role or is_active")
        return self


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses=ORGANIZER_OR_ADMIN,
)


@router.get("/users", response_model=UserPageResponse, summary="List users")
def list_users(
    email: Annotated[
        str | None,
        Query(
            max_length=255,
            description="Case-insensitive prefix search on the email; blank means no filter.",
            examples=["ana.pe"],
        ),
    ] = None,
    page: PageNumber = 1,
    size: PageSize = 10,
    service: UserAdminService = Depends(get_user_admin_service),
) -> UserPageResponse:
    """Paginated user accounts ordered by id, optionally filtered by `email`. Admin only.

    `email` is a case-insensitive prefix match on the login email (wildcard characters are
    matched literally). A blank value applies no filter. `total` and `pages` describe the
    filtered set.
    """
    result = service.list_users(page=page, size=size, email_prefix=email)
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
    summary="Update a user's profile, role or active flag",
    responses=combine(
        USER_NOT_FOUND,
        conflicts(
            "The change clashes with another account or with the admin's own account.",
            {
                "email_taken": ("Email already used by another user", EMAIL_TAKEN_DETAIL),
                "self_lockout": (
                    "An admin cannot demote or deactivate their own account",
                    SELF_LOCKOUT_DETAIL,
                ),
            },
        ),
        validation_error(
            "Invalid name or email, an unknown role, or none of the fields was sent.",
            ["body", "email"],
            "value is not a valid email address",
            "value_error",
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

    Send only the fields to change, at least one: `full_name`, `email`, `role` (`admin`,
    `organizer`, `attendee`) and/or `is_active`. Name and email follow the registration rules
    (trimmed name of 1 to 200 characters; email trimmed and lowercased, unique). Changing the
    email changes the login name; tokens already issued stay valid because they identify the
    user by id. Deactivating an account blocks its login and any token already issued.

    An admin may edit their own name and email, but cannot change their own role away from
    `admin` nor deactivate themselves (409); another admin has to do it.
    """
    return service.update_user(
        actor,
        user_id,
        role=body.role,
        is_active=body.is_active,
        full_name=body.full_name,
        email=body.email,
    )
