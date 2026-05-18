from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BookingSlotDetail(BaseModel):
    """Details of a booking slot in an order"""

    id: int
    court_id: int
    slot_date: date
    start_time: time
    end_time: time
    is_available: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Request to create an order with multiple booking slots"""

    court_id: int
    booking_slot_ids: list[int]


class OrderRead(BaseModel):
    """Basic order information"""

    id: int
    user_id: int
    court_id: int
    booking_date: date | None = None
    total_price: Decimal | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(BaseModel):
    """Detailed order information including booking slots"""

    id: int
    user_id: int
    court_id: int
    booking_date: date | None = None
    total_price: Decimal | None = None
    created_at: datetime
    booking_slots: list[BookingSlotDetail] = []

    model_config = ConfigDict(from_attributes=True)
