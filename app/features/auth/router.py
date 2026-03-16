from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.user.models import User
from app.features.user.schemas import UserRead

from .dependencies import get_current_active_user
from .openapi import LOGIN_OPENAPI_EXTRA
from .schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from .service import login_user, refresh_access_token, register_user

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
        200: {"description": "User created successfully"},
        400: {"description": "Email already registered"},
        422: {"description": "Request validation failed"},
        500: {"description": "Could not create user"},
    },
)
async def register(
    register_data: RegisterRequest,
    db: DbSessionDep,
):
    """Register endpoint that creates a user and returns an access and refresh tokens."""
    return await register_user(db, register_data)


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


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User Profile",
    description="Returns profile data for the authenticated user.",
    responses={
        200: {"description": "Profile data returned successfully"},
        401: {"description": "Access token is missing or invalid"},
        403: {"description": "Current user is inactive"},
    },
)
async def get_current_user_info(
    current_user: CurrentUserDep,
):
    """Get the current authenticated user's information"""
    return current_user
