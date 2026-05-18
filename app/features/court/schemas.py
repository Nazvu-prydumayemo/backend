from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class CourtBase(BaseModel):
    """Base schema for Court with common fields used in creation and reading."""

    name: str
    surface_type: str
    is_indoor: bool
    price_per_hour: float
    description: str | None = None
    location: str | None = None
    working_hours: str | None = None


class CourtCreate(CourtBase):
    """Schema for creating a new Court. Inherits all fields from CourtBase."""


class CourtUpdate(BaseModel):
    """Schema for updating an existing Court. All fields are optional."""

    name: str | None = None
    surface_type: str | None = None
    is_indoor: bool | None = None
    price_per_hour: float | None = None
    description: str | None = None
    location: str | None = None
    working_hours: str | None = None


class CourtRead(CourtBase):
    """Schema for reading Court data from the database."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCourtRead(BaseModel):
    """Schema for paginated court results."""

    items: list[CourtRead]
    total: int
    skip: int
    limit: int


# CourtSchedule Schemas
class CourtScheduleBase(BaseModel):
    """Base schema for CourtSchedule."""

    day_of_week: int  # 0=Monday, 6=Sunday
    opening_time: time | None = None  # NULL = court closed on this day
    closing_time: time | None = None


class CourtScheduleCreate(CourtScheduleBase):
    """Schema for creating a court schedule entry."""


class CourtScheduleUpdate(BaseModel):
    """Schema for updating a court schedule entry. All fields are optional."""

    day_of_week: int | None = None
    opening_time: time | None = None
    closing_time: time | None = None


class CourtScheduleRead(CourtScheduleBase):
    """Schema for reading court schedule data from the database."""

    id: int
    court_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# BookingSlot Schemas
class BookingSlotBase(BaseModel):
    """Base schema for BookingSlot."""

    start_time: time
    end_time: time


class BookingSlotRead(BookingSlotBase):
    """Schema for reading booking slot data from the database."""

    id: int
    court_id: int
    slot_date: date
    is_available: bool
    order_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailableSlotsResponse(BaseModel):
    """Schema for available slots response."""

    court_id: int
    slot_date: date
    available_slots: list[BookingSlotRead]
    total_slots: int
