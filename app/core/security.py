import asyncio
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import AfterValidator

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    """Hash a plaintext password using the configured passlib context."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pwd_context.hash, password)


async def verify_password(password: str, hashed: str) -> bool:
    """Return True when a plaintext password matches the stored hash."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, pwd_context.verify, password, hashed)


def generate_reset_code() -> str:
    """Generate a random 6-digit reset code.

    Returns:
        str: A 6-digit code as a string.
    """
    return str(secrets.randbelow(1000000)).zfill(6)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed short-lived JWT access token from the provided payload."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a signed long-lived JWT refresh token from the provided payload."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token, returning None when invalid or expired."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return None


def validate_password_regex(v: str) -> str:

    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"

    if not re.match(pattern, v):
        raise ValueError(
            "Password is too weak. Please ensure it meets all complexity requirements."
        )
    return v


StrongPassword = Annotated[str, AfterValidator(validate_password_regex)]
