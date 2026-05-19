from collections.abc import Sequence
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BookingSlot, Court, CourtSchedule
from .schemas import CourtCreate, CourtUpdate
from .utils import get_available_slots as utils_get_available_slots


async def get_courts(
    db: AsyncSession, skip: int = 0, limit: int = 10
) -> tuple[Sequence[Court], int]:
    """Retrieve paginated courts from the database.

    Args:
        db: Database session
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return

    Returns:
        Tuple of (courts, total_count)
    """

    count_result = await db.execute(select(Court))
    total_count = len(count_result.scalars().all())

    result = await db.execute(select(Court).offset(skip).limit(limit))
    courts = result.scalars().all()

    return courts, total_count


async def get_court_by_id(db: AsyncSession, court_id: int) -> Court | None:
    """Retrieve a court by its ID. Returns None if not found."""
    query = select(Court).where(Court.id == court_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_court(db: AsyncSession, data: CourtCreate) -> Court:
    """Create a new court with the provided data."""
    new_court = Court(**data.model_dump())

    db.add(new_court)
    await db.commit()
    await db.refresh(new_court)

    return new_court


async def update_court(db: AsyncSession, court_id: int, data: CourtUpdate) -> Court | None:
    """Update an existing court with the provided data. Only updates provided fields."""
    court = await get_court_by_id(db, court_id)

    if not court:
        return None

    update_data = data.model_dump(exclude_unset=True, exclude_none=True)

    for key, value in update_data.items():
        setattr(court, key, value)

    await db.commit()
    await db.refresh(court)

    return court


async def delete_court_by_id(db: AsyncSession, court_id: int) -> Court | None:
    """Delete a court by its ID. Returns the deleted court or None if not found."""
    court = await get_court_by_id(db, court_id)

    if not court:
        return None

    await db.delete(court)
    await db.commit()

    return court


# Court Schedule Service Methods


async def set_court_schedule(
    db: AsyncSession,
    court_id: int,
    day_of_week: int,
    opening_time: time | None,
    closing_time: time | None,
) -> CourtSchedule | None:
    """Set or update the schedule for a court on a specific day of the week.

    Args:
        db: Database session
        court_id: ID of the court
        day_of_week: Day of week (0=Monday, 6=Sunday)
        opening_time: Opening time or None if court is closed on this day
        closing_time: Closing time or None if court is closed on this day

    Returns:
        The created or updated schedule record, or None if court doesn't exist
    """
    # Check if court exists
    court = await get_court_by_id(db, court_id)
    if not court:
        return None

    # Check if schedule already exists
    query = select(CourtSchedule).where(
        (CourtSchedule.court_id == court_id) & (CourtSchedule.day_of_week == day_of_week)
    )
    result = await db.execute(query)
    schedule = result.scalar_one_or_none()

    if schedule:
        # Update existing schedule
        schedule.opening_time = opening_time
        schedule.closing_time = closing_time
    else:
        # Create new schedule
        schedule = CourtSchedule(
            court_id=court_id,
            day_of_week=day_of_week,
            opening_time=opening_time,
            closing_time=closing_time,
        )
        db.add(schedule)

    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_court_schedule(db: AsyncSession, court_id: int) -> Sequence[CourtSchedule]:
    """Get the weekly schedule for a court (all 7 days).

    Args:
        db: Database session
        court_id: ID of the court

    Returns:
        Sequence of CourtSchedule records for the court (0-7 entries)
    """
    query = (
        select(CourtSchedule)
        .where(CourtSchedule.court_id == court_id)
        .order_by(CourtSchedule.day_of_week)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_available_slots(
    db: AsyncSession, court_id: int, target_date: date
) -> Sequence[BookingSlot]:
    """Get available 30-minute slots for a court on a specific date.

    This function:
    1. Validates that the date is within the allowed range (today to +7 days)
    2. Checks if slots are already generated for this date
    3. If not, generates them based on the court's weekly schedule
    4. Returns all available slots

    Args:
        db: Database session
        court_id: ID of the court
        target_date: Date for which to retrieve slots

    Returns:
        Sequence of available BookingSlot records

    Raises:
        ValueError: If target_date is outside the allowed range (today to +7 days)
    """
    from .utils import validate_slot_date

    # Validate date is within allowed range
    is_valid, error_message = validate_slot_date(target_date)
    if not is_valid:
        raise ValueError(error_message)

    return await utils_get_available_slots(db, court_id, target_date)


async def get_court_with_schedule(db: AsyncSession, court_id: int) -> Court | None:
    """Get a court with its complete weekly schedule loaded.

    Args:
        db: Database session
        court_id: ID of the court

    Returns:
        Court with schedules, or None if not found
    """
    return await get_court_by_id(db, court_id)
