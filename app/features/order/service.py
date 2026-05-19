from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.court.models import BookingSlot, Court

from .models import Order
from .schemas import OrderCreate


class OrderValidationError(Exception):
    """Raised when order validation fails"""

    def __init__(self, message: str, unavailable_slots: list[dict] | None = None):
        self.message = message
        self.unavailable_slots = unavailable_slots or []
        super().__init__(self.message)


async def create_order(db: AsyncSession, user_id: int, data: OrderCreate) -> Order:
    """Create a new order for the current user."""
    new_order = Order(user_id=user_id, court_id=data.court_id)

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order


async def create_order_with_slots(
    db: AsyncSession,
    user_id: int,
    court_id: int,
    booking_slot_ids: list[int],
) -> Order:
    """Create an order with multiple booking slots.

    Validates that:
    - All slots exist and belong to the court
    - All slots are available
    - All slot dates are within the allowed range (today to +7 days)
    Uses atomic transaction: all slots marked unavailable together or none.

    Args:
        db: Database session
        user_id: ID of the user creating the order
        court_id: ID of the court being booked
        booking_slot_ids: List of booking slot IDs to book

    Returns:
        Created Order with populated booking_slots relationship

    Raises:
        OrderValidationError: If validation fails with details of unavailable slots or invalid dates
    """
    # Fetch all requested booking slots
    query = select(BookingSlot).where(BookingSlot.id.in_(booking_slot_ids))
    result = await db.execute(query)
    slots = result.scalars().all()

    # Validate: all slots exist
    if len(slots) != len(booking_slot_ids):
        found_ids = {slot.id for slot in slots}
        missing_ids = set(booking_slot_ids) - found_ids
        raise OrderValidationError(f"Some booking slots not found: {missing_ids}")

    # Validate: all slots belong to the requested court
    invalid_slots = [slot for slot in slots if slot.court_id != court_id]
    if invalid_slots:
        raise OrderValidationError(
            f"Slots {[s.id for s in invalid_slots]} do not belong to court {court_id}"
        )

    # Validate: all slots are within allowed date range (today to +7 days)
    from datetime import datetime, timedelta

    today = datetime.now(UTC).date()
    max_date = today + timedelta(days=7)

    out_of_range_slots = []
    for slot in slots:
        if slot.slot_date < today or slot.slot_date > max_date:
            out_of_range_slots.append(
                {
                    "id": slot.id,
                    "slot_date": slot.slot_date.isoformat(),
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat(),
                    "reason": "Date is outside allowed range (today to +7 days)",
                }
            )

    if out_of_range_slots:
        raise OrderValidationError(
            f"{len(out_of_range_slots)} slot(s) are outside the allowed booking range (today to +7 days)",
            unavailable_slots=out_of_range_slots,
        )

    # Validate: all slots are available (strict mode - all or nothing)
    unavailable_slots = []
    for slot in slots:
        if not slot.is_available:
            unavailable_slots.append(
                {
                    "id": slot.id,
                    "slot_date": slot.slot_date.isoformat(),
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat(),
                }
            )

    if unavailable_slots:
        raise OrderValidationError(
            f"{len(unavailable_slots)} slot(s) are not available",
            unavailable_slots=unavailable_slots,
        )

    # Fetch court to get price_per_hour
    court_query = select(Court).where(Court.id == court_id)
    court_result = await db.execute(court_query)
    court = court_result.scalar_one_or_none()

    if not court:
        raise OrderValidationError(f"Court {court_id} not found")

    # Calculate total price: price_per_hour * (number_of_slots * 0.5) hours
    # Each slot = 30 minutes = 0.5 hours
    total_hours = len(slots) * 0.5
    total_price = Decimal(str(court.price_per_hour)) * Decimal(str(total_hours))

    # Get booking_date from first slot
    booking_date = slots[0].slot_date if slots else None

    # Create order with calculated values
    new_order = Order(
        user_id=user_id,
        court_id=court_id,
        booking_date=booking_date,
        total_price=total_price,
    )
    db.add(new_order)

    # Flush to get the order ID without committing yet
    await db.flush()

    # Update all slots to mark them unavailable and associate with order
    for slot in slots:
        slot.is_available = False
        slot.order_id = new_order.id

    # Commit the transaction atomically
    await db.commit()

    # Fetch the created order with its relationship loaded
    order_query = (
        select(Order).where(Order.id == new_order.id).options(selectinload(Order.booking_slots))
    )
    order_result = await db.execute(order_query)
    return order_result.scalar_one()


async def get_orders_by_user_id(db: AsyncSession, user_id: int) -> Sequence[Order]:
    """Retrieve all orders belonging to a specific user."""
    query = select(Order).where(Order.user_id == user_id).options(selectinload(Order.booking_slots))
    result = await db.execute(query)
    return result.scalars().all()


async def get_order_by_id(db: AsyncSession, order_id: int) -> Order | None:
    """Retrieve an order by its ID. Returns None if not found."""
    query = select(Order).where(Order.id == order_id).options(selectinload(Order.booking_slots))
    result = await db.execute(query)
    return result.scalar_one_or_none()
