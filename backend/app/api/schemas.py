"""Request/response DTOs. Password hashes are never part of any response."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.domain.enums import Role
from app.domain.user import MAX_FULL_NAME_LENGTH, MIN_PASSWORD_LENGTH

FullName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_FULL_NAME_LENGTH)
]


class RegisterRequest(BaseModel):
    """Data needed to create an account (organizer role)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "ana@example.com",
                    "password": "s3cret-pass",
                    "full_name": "Ana Perez",
                }
            ]
        }
    )

    email: EmailStr = Field(description="Unique email address, used as the login name.")
    full_name: FullName = Field(
        description=(
            "Person's full name, shown in the app. Surrounding whitespace is trimmed; "
            f"1 to {MAX_FULL_NAME_LENGTH} characters."
        ),
        examples=["Ana Perez"],
    )
    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description=f"Password, at least {MIN_PASSWORD_LENGTH} characters long.",
    )


class LoginRequest(BaseModel):
    """Credentials exchanged for an access token."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "ana@example.com", "password": "s3cret-pass"}]}
    )

    email: str = Field(description="Email address used at registration.")
    password: str = Field(description="Account password.")


class TokenResponse(BaseModel):
    """JWT to send as ``Authorization: Bearer <access_token>``."""

    access_token: str = Field(
        description="Signed JWT identifying the user.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.signature"],
    )
    token_type: str = Field(
        default="bearer", description="Token scheme; always `bearer`.", examples=["bearer"]
    )


class UserResponse(BaseModel):
    """Public view of a user account."""

    id: int = Field(description="User identifier.", examples=[2])
    email: str = Field(description="Account email address.", examples=["ana@example.com"])
    full_name: str = Field(description="Person's full name.", examples=["Ana Perez"])
    role: Role = Field(description="Authorization role of the user.", examples=["attendee"])
    is_active: bool = Field(
        description="Deactivated accounts can no longer log in or use existing tokens.",
        examples=[True],
    )
