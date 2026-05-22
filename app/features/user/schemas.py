import enum
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.security import StrongPassword


class UserRoleEnum(enum.IntEnum):
    ADMIN = 1
    MODERATOR = 2
    USER = 3


class UserBase(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr


class UserCreate(UserBase):
    password: StrongPassword
    role_id: UserRoleEnum


class UserUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    email: EmailStr | None = None
    password: StrongPassword | None = None
    role_id: UserRoleEnum | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    id: int
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True


class DeleteAccountRequest(BaseModel):
    password: str


class UserProfileUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: StrongPassword


class ExportedSlot(BaseModel):
    court_id: int
    slot_date: date
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class ExportedOrder(BaseModel):
    order_id: int
    court_id: int
    booking_date: date | None = None
    total_price: Decimal | None = None
    created_at: datetime
    slots: list[ExportedSlot] = []

    model_config = ConfigDict(from_attributes=True)


class UserDataExport(BaseModel):
    profile: UserRead
    orders: list[ExportedOrder]
