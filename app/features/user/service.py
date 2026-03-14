from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password, verify_password

from .models import User
from .schemas import UserCreate


async def get_users(db: AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User).options(selectinload(User.role)))
    return result.scalars().all()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    query = select(User).where(User.id == user_id).options(selectinload(User.role))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, user_email: str) -> User | None:
    query = select(User).where(User.email == user_email).options(selectinload(User.role))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User | None:
    existing_user = await get_user_by_email(db, data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = await hash_password(data.password)

    new_user = User(
        firstname=data.firstname,
        lastname=data.lastname,
        email=data.email,
        password=hashed_password,
        role_id=data.role_id.value,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return await get_user_by_id(db, new_user.id)


async def delete_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    user = await get_user_by_id(db, user_id)

    if not user:
        return None

    await db.delete(user)
    await db.commit()

    return user


async def update_user_profile(
    db: AsyncSession, user: User, firstname: str | None = None, lastname: str | None = None
) -> User:
    """Update user's firstname and lastname."""
    if firstname is not None:
        user.firstname = firstname
    if lastname is not None:
        user.lastname = lastname

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def change_user_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> User:
    """Change user's password after verifying the current password."""

    password_valid = await verify_password(current_password, user.password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the old password",
        )

    hashed_password = await hash_password(new_password)
    user.password = hashed_password

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
