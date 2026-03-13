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


@router.post("/register", response_model=Token, status_code=201)
async def register(
    register_data: RegisterRequest,
    db: DbSessionDep,
):
    """Register endpoint that creates a user and returns access and refresh tokens."""
    return await register_user(db, register_data)


@router.post("/login", response_model=Token, openapi_extra=LOGIN_OPENAPI_EXTRA)
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
                detail="Form login requires username and password",
            )

        return await login_user(db, username, password)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Unsupported Content-Type for login",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh the access token using a refresh token"""
    return await refresh_access_token(refresh_data.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: CurrentUserDep,
):
    """Get the current authenticated user's information"""
    return current_user
