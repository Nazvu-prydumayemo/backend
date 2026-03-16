from typing import Any

from pydantic import BaseModel, EmailStr


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
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
