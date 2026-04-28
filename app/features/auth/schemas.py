from pydantic import BaseModel, EmailStr

from app.core.security import StrongPassword


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: StrongPassword


class RefreshTokenRequest(BaseModel):
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
