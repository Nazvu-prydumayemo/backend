"""Court, CourtSchedule, and BookingSlot SQLAlchemy ORM models."""

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.features.order.models import Order


class Court(Base):
    """ORM model representing a tennis court with pricing and location details."""

    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    name: Mapped[str] = mapped_column(String, nullable=False)

    surface_type: Mapped[str] = mapped_column(String, nullable=False)

    price_per_hour: Mapped[float] = mapped_column(Float, nullable=False)

    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    location: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    # Relationships
    schedules: Mapped[list["CourtSchedule"]] = relationship(
        "CourtSchedule",
        back_populates="court",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list,
    )
    booking_slots: Mapped[list["BookingSlot"]] = relationship(
        "BookingSlot",
        back_populates="court",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list,
    )


class CourtSchedule(Base):
    """Weekly schedule configuration for a court (one entry per day-of-week)"""

    __tablename__ = "court_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)

    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday, 6=Sunday

    opening_time: Mapped[time | None] = mapped_column(
        Time, nullable=True
    )  # NULL = court closed on this day

    closing_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    # Relationships
    court: Mapped["Court"] = relationship("Court", back_populates="schedules", init=False)

    __table_args__ = (UniqueConstraint("court_id", "day_of_week", name="uq_court_schedule_day"),)


class BookingSlot(Base):
    """30-minute booking slot for a court on a specific date"""

    __tablename__ = "booking_slots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)

    slot_date: Mapped[date] = mapped_column(Date, nullable=False)

    start_time: Mapped[time] = mapped_column(Time, nullable=False)

    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True, default=None
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), init=False
    )

    # Relationships
    court: Mapped["Court"] = relationship("Court", back_populates="booking_slots", init=False)
    order: Mapped["Order"] = relationship("Order", back_populates="booking_slots", init=False)

    __table_args__ = (
        UniqueConstraint("court_id", "slot_date", "start_time", name="uq_booking_slot"),
        Index("idx_court_date", "court_id", "slot_date"),
        Index("idx_court_availability", "court_id", "is_available"),
    )
