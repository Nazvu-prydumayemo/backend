from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_code,
    hash_password,
    verify_password,
)
from app.features.auth.models import PasswordReset
from app.features.user.schemas import UserCreate, UserRoleEnum
from app.features.user.service import (
    create_user,
    get_user_by_email,
)

from .schemas import RegisterRequest, Token


async def login_user(db: AsyncSession, email: str, password: str) -> Token:
    """Login a user and return access and refresh tokens"""
    user = await get_user_by_email(db, email)

    if not user or not await verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

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
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        ) from exc

    if created_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(created_user.id), "email": created_user.email},
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(
        data={"sub": str(created_user.id), "email": created_user.email}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def refresh_access_token(refresh_token: str) -> Token:
    """Refresh the access token using a refresh token"""
    payload = decode_token(refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id: int | None = payload.get("sub")
    email: str | None = payload.get("email")

    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_id), "email": email},
        expires_delta=access_token_expires,
    )
    new_refresh_token = create_refresh_token(data={"sub": str(user_id), "email": email})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


async def request_password_reset(db: AsyncSession, email: str) -> str:
    """
    Generate and store a 6-digit password reset code for a user.

    Args:
        db (AsyncSession): Database session.
        email (str): User email address.

    Returns:
        str: The 6-digit reset code.

    Raises:
        HTTPException: If user not found or user is inactive.
    """
    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        ) from None

    reset_code = generate_reset_code()

    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(minutes=15)

    await db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))

    reset_record = PasswordReset(
        user_id=user.id,
        code=reset_code,
        created_at=created_at,
        expires_at=expires_at,
    )

    db.add(reset_record)
    await db.commit()

    return reset_code


async def verify_reset_code(db: AsyncSession, email: str, code: str) -> bool:
    """
    Verify that the reset code is valid and hasn't expired.

    Args:
        db (AsyncSession): Database session.
        email (str): User email address.
        code (str): The 6-digit reset code to verify.

    Returns:
        bool: True if code is valid.

    Raises:
        HTTPException: If code is invalid, expired, or user not found.
    """
    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    # Query for valid reset code
    query = select(PasswordReset).where(
        (PasswordReset.user_id == user.id)
        & (PasswordReset.code == code)
        & (PasswordReset.expires_at > datetime.now(UTC))
    )
    result = await db.execute(query)
    reset_record = result.scalar_one_or_none()

    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset code",
        ) from None

    return True


async def confirm_password_reset(
    db: AsyncSession, email: str, code: str, new_password: str
) -> dict:
    """
    Reset user password after validating the reset code.

    Args:
        db (AsyncSession): Database session.
        email (str): User email address.
        code (str): The 6-digit reset code.
        new_password (str): New password (must meet complexity requirements).

    Returns:
        dict: Message confirming password reset.

    Raises:
        HTTPException: If code invalid, expired, or user not found.
    """
    # Verify the code first
    await verify_reset_code(db, email, code)

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    hashed_password = await hash_password(new_password)
    user.password = hashed_password

    db.add(user)

    await db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))

    await db.commit()

    return {"message": "Password reset successfully"}
