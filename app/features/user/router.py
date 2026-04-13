from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password
from app.features.auth.dependencies import admin_guard, get_current_active_user, staff_guard

from .models import User
from .schemas import ChangePasswordRequest, DeleteAccountRequest, UserProfileUpdate, UserRead
from .service import (
    change_user_password,
    delete_user_by_id,
    get_user_by_id,
    get_users,
    update_user_profile,
)

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/", response_model=list[UserRead])
async def list_all_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(staff_guard)],
):
    return await get_users(db)


@users_router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@users_router.delete(
    "/{user_id}",
    responses={
        200: {"description": "User deleted successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        403: {"description": "Forbidden - Admin access required"},
    },
)
async def delete_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Delete a user by ID (admin only).

    Only administrators can delete users.

    Errors:
    - **403**: When the user is not an administrator
    - **401**: When authentication token is invalid or missing
    """
    await delete_user_by_id(db, user_id)
    return {"message": "User deleted successfully"}


account_router = APIRouter(prefix="/account", tags=["account"])


@account_router.get("/me", response_model=UserRead)
async def get_account_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get the current authenticated user's account information"""
    return current_user


@account_router.patch(
    "/profile",
    response_model=UserRead,
    responses={
        200: {"description": "Profile updated successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        422: {"description": "Validation error - Invalid input data"},
    },
)
async def update_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    profile_update: UserProfileUpdate,
):
    """Update the current user's profile (firstname and lastname only).

    - **firstname** (optional): User's first name
    - **lastname** (optional): User's last name

    Returns the updated user profile.
    """
    updated_user = await update_user_profile(
        db,
        current_user,
        firstname=profile_update.firstname,
        lastname=profile_update.lastname,
    )
    return updated_user


@account_router.post(
    "/change-password",
    response_model=UserRead,
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Bad Request - New password cannot be the same as the old password"},
        401: {"description": "Unauthorized - Invalid authentication or incorrect current password"},
        422: {"description": "Validation error - Invalid input data"},
    },
)
async def change_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    password_change: ChangePasswordRequest,
):
    """Change the current user's password after verifying the current password.

    - **current_password**: The user's current password for verification
    - **new_password**: The new password to set

    Errors:
    - **401**: When the current password is incorrect
    - **400**: When the new password is the same as the old password

    Returns the updated user profile on success.
    """
    updated_user = await change_user_password(
        db,
        current_user,
        current_password=password_change.current_password,
        new_password=password_change.new_password,
    )
    return updated_user


@account_router.post(
    "/delete",
    responses={
        200: {"description": "Account deleted successfully"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        403: {"description": "Forbidden - Incorrect password, account deletion aborted"},
        422: {"description": "Validation error - Invalid input data"},
    },
)
async def delete_account(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    delete_request: DeleteAccountRequest,
):
    """Delete the current user's account after password verification.

    This endpoint permanently deletes the authenticated user's account.
    Password verification is required for security.

    - **password**: User's current password for verification

    Errors:
    - **403**: When the provided password is incorrect
    - **401**: When authentication token is invalid or missing

    Returns a success message and user ID upon successful deletion.
    """
    password_valid = await verify_password(delete_request.password, current_user.password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not verify identity. Account deletion aborted.",
        )

    await delete_user_by_id(db, current_user.id)

    return {"message": "Account deleted successfully"}
