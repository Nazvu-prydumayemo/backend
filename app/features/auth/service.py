from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.features.user.schemas import UserCreate, UserRoleEnum
from app.features.user.service import create_user, get_user_by_email

from .errors import raise_auth_error
from .schemas import RegisterRequest, Token


async def login_user(db: AsyncSession, email: str, password: str) -> Token:
    """Login a user and return access and refresh tokens"""
    user = await get_user_by_email(db, email)

    if not user or not await verify_password(password, user.password):
        raise_auth_error("invalid_credentials")

    if not user.is_active:
        raise_auth_error("inactive_user")

    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def register_user(db: AsyncSession, register_data: RegisterRequest) -> Token:
    """Register a user and return access and refresh tokens."""
    try:
        created_user = await create_user(
            db,
            UserCreate(
                firstname=register_data.firstname,
                lastname=register_data.lastname,
                email=register_data.email,
                password=register_data.password,
                role_id=UserRoleEnum.USER,
            ),
        )
    except HTTPException as exc:
        if exc.status_code == 400 and exc.detail == "Email already registered":
            raise_auth_error("email_already_registered")
        raise_auth_error("user_creation_failed")
    except Exception:
        raise_auth_error("user_creation_failed")

    if created_user is None:
        raise_auth_error("user_creation_failed")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": created_user.id, "email": created_user.email},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(data={"sub": created_user.id, "email": created_user.email})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def refresh_access_token(refresh_token: str) -> Token:
    """Refresh the access token using a refresh token"""
    payload = decode_token(refresh_token)

    if payload is None:
        raise_auth_error("invalid_refresh_token")

    # Check token type
    if payload.get("type") != "refresh":
        raise_auth_error("invalid_token_type")

    user_id: int | None = payload.get("sub")
    email: str | None = payload.get("email")

    if user_id is None or email is None:
        raise_auth_error("invalid_refresh_token")

    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id, "email": email},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(data={"sub": user_id, "email": email})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )
