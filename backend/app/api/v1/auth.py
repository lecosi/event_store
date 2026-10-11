from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service, get_current_user
from app.api.openapi_responses import UNAUTHORIZED, conflict, error_response
from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.application.auth_service import AuthService
from app.domain.user import UserAccount

router = APIRouter(tags=["auth"])


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    responses=conflict("The email is already registered.", "Email already registered"),
)
def register(body: RegisterRequest, auth: AuthService = Depends(get_auth_service)) -> UserAccount:
    """Create an account. Public endpoint.

    The new user always gets the `organizer` role (the client cannot choose a role), so it can
    create and manage its own events; an admin can change it later.
    The password must have at least 8 characters, the email must be unique and the full name
    is required (1 to 200 characters, surrounding whitespace is trimmed).
    """
    return auth.register(body.email, body.password, body.full_name)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Log in and get an access token",
    responses=error_response(
        401, "Unknown email, wrong password or deactivated account.", "Invalid email or password"
    ),
)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)) -> TokenResponse:
    """Exchange email and password for a JWT. Public endpoint.

    Send the returned token as `Authorization: Bearer <token>` (or use **Authorize** above).
    """
    return TokenResponse(access_token=auth.login(body.email, body.password))


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get the current user",
    responses=UNAUTHORIZED,
)
def read_me(user: UserAccount = Depends(get_current_user)) -> UserAccount:
    """Return the profile (id, email, full name, role, active flag) of the authenticated user."""
    return user
