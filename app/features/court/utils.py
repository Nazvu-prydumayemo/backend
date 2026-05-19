"""Utility functions for court scheduling and booking slot management."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BookingSlot, Court, CourtSchedule


def validate_slot_date(target_date: date) -> tuple[bool, str]:
    """Validate that a slot date is within the allowed booking range (today to +7 days).

    Args:
        target_date: Date to validate

    Returns:
        Tuple of (is_valid, error_message). is_valid is True if date is valid, False otherwise.
    """
    # Get today's date in UTC
    today = datetime.now(UTC).date()
    max_date = today + timedelta(days=7)

    if target_date < today:
        return False, f"Cannot query slots for past dates. Today is {today}."

    if target_date > max_date:
        return False, f"Can only query slots up to {max_date} ({7} days from today)."

    return True, ""


def get_30min_slots(opening_time: time, closing_time: time) -> list[tuple[time, time]]:
    """Generate 30-minute interval slots between opening and closing times.

    Args:
        opening_time: Court opening time
        closing_time: Court closing time

    Returns:
        List of (start_time, end_time) tuples for each 30-minute slot
    """
    slots = []

    # Convert times to minutes for easier calculation
    current_minutes = opening_time.hour * 60 + opening_time.minute
    close_minutes = closing_time.hour * 60 + closing_time.minute

    while current_minutes < close_minutes:
        start_hour = current_minutes // 60
        start_min = current_minutes % 60
        start_time = time(hour=start_hour, minute=start_min)

        end_minutes = current_minutes + 30
        end_hour = end_minutes // 60
        end_min = end_minutes % 60
        end_time = time(hour=end_hour, minute=end_min)

        slots.append((start_time, end_time))
        current_minutes = end_minutes

    return slots


async def generate_slots_for_date(
    db: AsyncSession, court_id: int, target_date: date
) -> list[BookingSlot]:
    """Generate BookingSlot records for a specific date based on court's weekly schedule.

    Args:
        db: Database session
        court_id: ID of the court
        target_date: Date for which to generate slots

    Returns:
        List of created BookingSlot records
    """
    # Get the court and its schedule
    court_query = select(Court).where(Court.id == court_id)
    result = await db.execute(court_query)
    court: Court | None = result.scalar_one_or_none()

    if not court:
        return []

    # Get the schedule for this day of week (0=Monday, 6=Sunday)
    day_of_week = target_date.weekday()
    schedule_query = select(CourtSchedule).where(
        and_(CourtSchedule.court_id == court_id, CourtSchedule.day_of_week == day_of_week)
    )
    schedule_result = await db.execute(schedule_query)
    schedule: CourtSchedule | None = schedule_result.scalar_one_or_none()

    # If no schedule or court is closed on this day, return empty list
    if not schedule or schedule.opening_time is None or schedule.closing_time is None:
        return []

    # Generate 30-minute slots
    slots_data = get_30min_slots(schedule.opening_time, schedule.closing_time)

    # Create BookingSlot records (skip if already exists)
    created_slots = []
    for start_time, end_time in slots_data:
        # Check if slot already exists
        existing_slot = await db.execute(
            select(BookingSlot).where(
                and_(
                    BookingSlot.court_id == court_id,
                    BookingSlot.slot_date == target_date,
                    BookingSlot.start_time == start_time,
                )
            )
        )

        if not existing_slot.scalar_one_or_none():
            slot = BookingSlot(
                court_id=court_id,
                slot_date=target_date,
                start_time=start_time,
                end_time=end_time,
                is_available=True,
            )
            db.add(slot)
            created_slots.append(slot)

    if created_slots:
        await db.commit()
        # Refresh slots to get IDs
        for slot in created_slots:
            await db.refresh(slot)

    return created_slots


async def get_available_slots(
    db: AsyncSession, court_id: int, target_date: date
) -> Sequence[BookingSlot]:
    """Get available 30-minute slots for a court on a specific date.

    Generates slots if they don't exist yet, then returns available ones.

    Args:
        db: Database session
        court_id: ID of the court
        target_date: Date for which to retrieve slots

    Returns:
        Sequence of available BookingSlot records
    """
    # First, try to generate slots for this date (if not already done)
    await generate_slots_for_date(db, court_id, target_date)

    # Now fetch available slots
    query = (
        select(BookingSlot)
        .where(
            and_(
                BookingSlot.court_id == court_id,
                BookingSlot.slot_date == target_date,
                BookingSlot.is_available,
            )
        )
        .order_by(BookingSlot.start_time)
    )

    result = await db.execute(query)
    return result.scalars().all()


async def validate_booking_slots(
    db: AsyncSession, court_id: int, booking_date: date, start_time: time, end_time: time
) -> tuple[bool, str]:
    """Validate that booking times are valid and slots are available.

    Args:
        db: Database session
        court_id: ID of the court
        booking_date: Date to book
        start_time: Booking start time
        end_time: Booking end time

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if booking is in the future
    now = datetime.now().date()
    if booking_date < now:
        return False, "Cannot book in the past"

    # Check if start_time < end_time
    if start_time >= end_time:
        return False, "Start time must be before end time"

    # Check if times are aligned with 30-minute boundaries
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    if start_minutes % 30 != 0:
        return False, "Start time must be aligned with 30-minute boundaries"

    if end_minutes % 30 != 0:
        return False, "End time must be aligned with 30-minute boundaries"

    # Check that all slots in the range are available
    query = select(BookingSlot).where(
        and_(
            BookingSlot.court_id == court_id,
            BookingSlot.slot_date == booking_date,
            BookingSlot.start_time >= start_time,
            BookingSlot.start_time < end_time,
            ~BookingSlot.is_available,
        )
    )

    result = await db.execute(query)
    unavailable_slots = result.scalars().all()

    if unavailable_slots:
        return False, "Some slots in the requested time range are not available"

    return True, ""


async def reserve_booking_slots(
    db: AsyncSession,
    order_id: int,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
) -> bool:
    """Mark booking slots as reserved (unavailable) and link them to an order.

    Args:
        db: Database session
        order_id: ID of the order
        court_id: ID of the court
        booking_date: Date to reserve
        start_time: Reservation start time
        end_time: Reservation end time

    Returns:
        True if successful, False otherwise
    """
    # Get all slots in the range
    query = select(BookingSlot).where(
        and_(
            BookingSlot.court_id == court_id,
            BookingSlot.slot_date == booking_date,
            BookingSlot.start_time >= start_time,
            BookingSlot.start_time < end_time,
        )
    )

    result = await db.execute(query)
    slots = result.scalars().all()

    if not slots:
        return False

    # Mark all slots as unavailable and link to order
    for slot in slots:
        slot.is_available = False
        slot.order_id = order_id

    await db.commit()
    return True


async def release_booking_slots(db: AsyncSession, order_id: int) -> bool:
    """Release (make available) all booking slots linked to an order.

    Args:
        db: Database session
        order_id: ID of the order

    Returns:
        True if slots were released, False otherwise
    """
    query = select(BookingSlot).where(BookingSlot.order_id == order_id)
    result = await db.execute(query)
    slots = result.scalars().all()

    if not slots:
        return False

    for slot in slots:
        slot.is_available = True
        slot.order_id = None

    await db.commit()
    return True


def calculate_booking_price(price_per_hour: float, start_time: time, end_time: time) -> float:
    """Calculate the total price of a booking based on duration.

    Args:
        price_per_hour: Price per hour in currency units
        start_time: Booking start time
        end_time: Booking end time

    Returns:
        Total price
    """
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    duration_minutes = end_minutes - start_minutes
    duration_hours = duration_minutes / 60

    return price_per_hour * duration_hours
