"""User and UserRole SQLAlchemy ORM models."""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(Base):
    """ORM model representing a user role (e.g. ADMIN, MODERATOR, USER)."""

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    users: Mapped[list["User"]] = relationship(back_populates="role", cascade="all, delete")


class User(Base):
    """ORM model representing a registered user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    firstname: Mapped[str] = mapped_column(String(50))
    lastname: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))

    role_id: Mapped[int] = mapped_column(ForeignKey("user_roles.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped["UserRole"] = relationship(back_populates="users", init=False)
