"""Order SQLAlchemy ORM model."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.features.court.models import BookingSlot


class Order(Base):
    """ORM model representing a court booking order placed by a user."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)

    booking_date: Mapped[date | None] = mapped_column(nullable=True, default=None)

    total_price: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2), nullable=True, default=None
    )

    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    # Relationships
    booking_slots: Mapped[list["BookingSlot"]] = relationship(
        "BookingSlot",
        back_populates="order",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list,
    )
