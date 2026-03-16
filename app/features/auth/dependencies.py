from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.features.user.models import User
from app.features.user.schemas import UserRoleEnum
from app.features.user.service import get_user_by_id

from .errors import raise_auth_error

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

TokenDep = Annotated[str, Depends(oauth2_scheme)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: TokenDep,
    db: DbSessionDep,
) -> User:
    """Dependency to get the current authenticated user"""
    payload = decode_token(token)
    if payload is None:
        raise_auth_error("credentials_validation_failed")

    # Check token type
    if payload.get("type") != "access":
        raise_auth_error("invalid_token_type")

    user_id: str | None = payload.get("sub")

    if user_id is None:
        raise_auth_error("credentials_validation_failed")

    user = await get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise_auth_error("credentials_validation_failed")

    if not user.is_active:
        raise_auth_error("inactive_user")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency to get the current active user"""
    if not current_user.is_active:
        raise_auth_error("inactive_user")
    return current_user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentActiveUserDep = Annotated[User, Depends(get_current_active_user)]


def require_roles(*allowed_roles: UserRoleEnum) -> Callable:
    """Dependency that allows only users with specific roles"""
    allowed_role_ids = {int(role) for role in allowed_roles}

    async def _role_guard(current_user: CurrentActiveUserDep) -> User:
        """Validate that the current active user has one of the allowed roles"""
        if current_user.role_id not in allowed_role_ids:
            raise_auth_error("forbidden_resource")
        return current_user

    return _role_guard


admin_guard = require_roles(UserRoleEnum.ADMIN)
staff_guard = require_roles(UserRoleEnum.ADMIN, UserRoleEnum.MODERATOR)
