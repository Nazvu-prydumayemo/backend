from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi_mail import NameEmail
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.email.service import email_service
from app.features.user.models import User
from app.features.user.service import get_user_by_email

from .dependencies import get_current_active_user
from .openapi import LOGIN_OPENAPI_EXTRA
from .schemas import (
    LoginRequest,
    PasswordResetCodeVerify,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from .service import (
    confirm_password_reset,
    login_user,
    refresh_access_token,
    register_user,
    request_password_reset,
    verify_reset_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_active_user)]


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    summary="Register New User",
    description=("Creates a new user account and returns an access token plus refresh token."),
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email already registered"},
        422: {"description": "Request validation failed"},
        500: {"description": "Could not create user"},
    },
)
async def register(
    register_data: RegisterRequest,
    db: DbSessionDep,
    background_tasks: BackgroundTasks,
):
    """Register endpoint that creates a user and returns access and refresh tokens.

    Welcome email is sent in the background without blocking the API response.
    """
    token = await register_user(db, register_data)

    background_tasks.add_task(
        email_service.send_welcome_email,
        NameEmail(email=register_data.email, name=register_data.firstname),
        register_data.firstname,
    )

    return token


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate User",
    description=(
        "Authenticates user credentials and returns fresh access and refresh tokens. "
        "Supports JSON (`email`, `password`) and form payload "
        "(`username`, `password`) for OAuth2-compatible clients."
    ),
    responses={
        200: {"description": "Logged in successfully"},
        401: {"description": "Incorrect email or password"},
        403: {"description": "User account is inactive"},
        415: {"description": "Unsupported content type. Use JSON or form-urlencoded"},
        422: {"description": "Login payload validation failed"},
    },
    openapi_extra=LOGIN_OPENAPI_EXTRA,
)
async def login(
    request: Request,
    db: DbSessionDep,
):
    """Login endpoint that returns access and refresh tokens"""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            raw_json = await request.json()
            login_data = LoginRequest.model_validate(raw_json)
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON login payload",
            ) from exc
        return await login_user(db, login_data.email, login_data.password)

    # for Swagger
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")

        if not isinstance(username, str) or not isinstance(password, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid login form payload",
            )

        return await login_user(db, username, password)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Unsupported Content-Type for login",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh Access Token",
    description=(
        "Exchanges a valid refresh token for a new access token and a rotated refresh token."
    ),
    responses={
        200: {"description": "Access token refreshed successfully"},
        401: {"description": "Refresh token is invalid or expired"},
    },
)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh the access token using a refresh token"""
    return await refresh_access_token(refresh_data.refresh_token)


@router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
    status_code=200,
    summary="Request Password Reset",
    description="Sends a 6-digit password reset code to the provided email address. Returns success regardless of whether the email exists for security.",
    responses={
        200: {"description": "Password reset code sent to email"},
        422: {"description": "Request validation failed"},
    },
)
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: DbSessionDep,
    background_tasks: BackgroundTasks,
):
    """
    Request a password reset by email.

    Generates a 6-digit reset code and sends it via email asynchronously.
    Returns success even if user doesn't exist (security measure).
    """
    try:
        reset_code = await request_password_reset(db, reset_request.email)

        user = await get_user_by_email(db, reset_request.email)
        if user:
            background_tasks.add_task(
                email_service.send_reset_password_email,
                NameEmail(email=reset_request.email, name=user.firstname),
                user.firstname,
                reset_code,
            )

        return PasswordResetResponse(
            message="If the email exists, a password reset code has been sent."
        )

    except HTTPException as e:
        if e.status_code in [404, 403]:
            return PasswordResetResponse(
                message="If the email exists, a password reset code has been sent."
            )
        raise


@router.post(
    "/verify-reset-code",
    response_model=PasswordResetResponse,
    status_code=200,
    summary="Verify Reset Code",
    description="Verifies that the provided reset code is valid and hasn't expired.",
    responses={
        200: {"description": "Reset code is valid"},
        401: {"description": "Invalid or expired reset code"},
        404: {"description": "User not found"},
        422: {"description": "Request validation failed"},
    },
)
async def verify_password_reset_code(
    verify_data: PasswordResetCodeVerify,
    db: DbSessionDep,
):
    """
    Verify the reset code before allowing password change.

    Validates that the code is correct and hasn't expired.
    """
    await verify_reset_code(db, verify_data.email, verify_data.code)
    return PasswordResetResponse(message="Reset code is valid. You can now reset your password.")


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    status_code=200,
    summary="Reset Password",
    description="Resets the user password using a valid 6-digit reset code.",
    responses={
        200: {"description": "Password reset successfully"},
        401: {"description": "Invalid or expired reset code"},
        404: {"description": "User not found"},
        422: {"description": "Request validation failed"},
    },
)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: DbSessionDep,
):
    """
    Reset password using a valid reset code.

    The code is validated, and the password is updated if valid.
    """
    return await confirm_password_reset(
        db, reset_data.email, reset_data.code, reset_data.new_password
    )
