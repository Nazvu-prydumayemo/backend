from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.user.models import User
from app.features.user.schemas import UserRead

from .dependencies import get_current_active_user
from .schemas import LoginRequest, RefreshTokenRequest, RegisterRequest, Token
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


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: DbSessionDep,
):
    """Login endpoint that returns access and refresh tokens"""
    return await login_user(db, login_data.email, login_data.password)


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
