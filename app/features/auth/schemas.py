"""Pydantic models for authentication request/response schemas."""

from pydantic import BaseModel, EmailStr

from app.core.security import StrongPassword


class Token(BaseModel):
    """Schema for access and refresh token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded JWT token payload data."""

    user_id: int | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    """Schema for login request payload."""

    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Schema for user registration request payload."""

    firstname: str
    lastname: str
    email: EmailStr
    password: StrongPassword


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request payload."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset."""

    email: EmailStr


class PasswordResetCodeVerify(BaseModel):
    """Request to verify the reset code."""

    email: EmailStr
    code: str


class PasswordResetConfirm(BaseModel):
    """Request to confirm password reset with code and new password."""

    email: EmailStr
    code: str
    new_password: StrongPassword


class PasswordResetResponse(BaseModel):
    """Response for password reset endpoints."""

    message: str
