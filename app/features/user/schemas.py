import enum

from pydantic import BaseModel, EmailStr


class UserRoleEnum(enum.IntEnum):
    ADMIN = 1
    MODERATOR = 2
    USER = 3


class UserBase(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    role_id: UserRoleEnum


class UserUpdate(BaseModel):
    firstname: str | None = None
    lastname: str | None = None
    email: EmailStr | None = None
    password: str | None = None
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
