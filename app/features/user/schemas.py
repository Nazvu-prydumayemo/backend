"""Pydantic models for user and account management schemas."""

import enum
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.security import StrongPassword


class UserRoleEnum(enum.IntEnum):
    """Enumeration of user roles: ADMIN, MODERATOR, USER."""

    ADMIN = 1
    MODERATOR = 2
    USER = 3


class UserBase(BaseModel):
    """Base schema for user data with common profile fields."""

    firstname: str
    lastname: str
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user with password and role."""

    password: StrongPassword
    role_id: UserRoleEnum


class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""

    firstname: str | None = None
    lastname: str | None = None
    email: EmailStr | None = None
    password: StrongPassword | None = None
    role_id: UserRoleEnum | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    """Schema for reading user data from the database."""

    id: int
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True


class DeleteAccountRequest(BaseModel):
    """Schema for account deletion request with password verification."""

    password: str


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile (firstname and lastname)."""

    firstname: str | None = None
    lastname: str | None = None


class ChangePasswordRequest(BaseModel):
    """Schema for changing password with current password verification."""

    current_password: str
    new_password: StrongPassword


class ExportedSlot(BaseModel):
    """Schema for a booking slot in a data export."""

    court_id: int
    slot_date: date
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class ExportedOrder(BaseModel):
    """Schema for an order with slots in a data export."""

    order_id: int
    court_id: int
    booking_date: date | None = None
    total_price: Decimal | None = None
    created_at: datetime
    slots: list[ExportedSlot] = []

    model_config = ConfigDict(from_attributes=True)


class UserDataExport(BaseModel):
    """Schema for full user data export response (GDPR Article 15)."""

    profile: UserRead
    orders: list[ExportedOrder]
