"""Request/response DTOs. Password hashes are never part of any response."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import Role
from app.domain.user import MIN_PASSWORD_LENGTH


class RegisterRequest(BaseModel):
    """Data needed to create an account (organizer role)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "ana@example.com", "password": "s3cret-pass"}]}
    )

    email: EmailStr = Field(description="Unique email address, used as the login name.")
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
    role: Role = Field(description="Authorization role of the user.", examples=["attendee"])
    is_active: bool = Field(
        description="Deactivated accounts can no longer log in or use existing tokens.",
        examples=[True],
    )
