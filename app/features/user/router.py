from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password
from app.features.auth.dependencies import admin_guard, get_current_active_user, staff_guard

from .models import User
from .schemas import DeleteAccountRequest, UserProfileUpdate, UserRead
from .service import delete_user_by_id, get_user_by_id, get_users, update_user_profile

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


account_router = APIRouter(prefix="/account", tags=["account"])


@account_router.get("/me", response_model=UserRead)
async def get_account_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get the current authenticated user's account information"""
    return current_user


@account_router.patch("/profile", response_model=UserRead)
async def update_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    profile_update: UserProfileUpdate,
):
    """Update the current user's profile (firstname and lastname only)."""
    updated_user = await update_user_profile(
        db,
        current_user,
        firstname=profile_update.firstname,
        lastname=profile_update.lastname,
    )
    return updated_user


@account_router.post("/delete")
async def delete_account(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    delete_request: DeleteAccountRequest,
):
    """Delete the current user's account after password verification."""
    password_valid = await verify_password(delete_request.password, current_user.password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not verify identity. Account deletion aborted.",
        )

    await delete_user_by_id(db, current_user.id)

    return {"message": "Account deleted successfully"}
