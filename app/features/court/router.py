from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import admin_guard, get_current_active_user
from app.features.user.models import User

from .schemas import (
    AvailableSlotsResponse,
    BookingSlotRead,
    CourtCreate,
    CourtRead,
    CourtScheduleCreate,
    CourtScheduleRead,
    CourtUpdate,
    PaginatedCourtRead,
)
from .service import (
    create_court,
    delete_court_by_id,
    get_available_slots,
    get_court_by_id,
    get_court_schedule,
    get_courts,
    set_court_schedule,
    update_court,
)

router = APIRouter(prefix="/courts", tags=["Courts"])


@router.post("/", response_model=CourtRead, status_code=status.HTTP_201_CREATED)
async def create_court_route(
    court_in: CourtCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Create a new court entry. Requires admin role."""
    return await create_court(db, court_in)


@router.get("/", response_model=PaginatedCourtRead, status_code=status.HTTP_200_OK)
async def get_courts_route(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = 0,
    limit: int = 10,
):
    """Retrieve all available courts with pagination. Requires authentication.

    Query Parameters:
        - skip: Number of records to skip (default: 0)
        - limit: Maximum number of records to return (default: 10)
    """
    courts, total_count = await get_courts(db, skip=skip, limit=limit)
    return PaginatedCourtRead(
        items=[CourtRead.model_validate(court) for court in courts],
        total=total_count,
        skip=skip,
        limit=limit,
    )


@router.get("/{court_id}", response_model=CourtRead, status_code=status.HTTP_200_OK)
async def get_court_route(
    court_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve a specific court by its ID. Requires authentication."""
    court = await get_court_by_id(db, court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )
    return court


@router.patch("/{court_id}", response_model=CourtRead, status_code=status.HTTP_200_OK)
async def update_court_route(
    court_id: int,
    court_in: CourtUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Update court information. Requires admin role."""
    court = await update_court(db, court_id, court_in)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )
    return court


@router.delete("/{court_id}", response_model=CourtRead, status_code=status.HTTP_200_OK)
async def delete_court_route(
    court_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Delete a court by its ID. Requires admin role."""
    court = await delete_court_by_id(db, court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )
    return court


# Court Schedule Endpoints


@router.post(
    "/{court_id}/schedule",
    response_model=CourtScheduleRead,
    status_code=status.HTTP_201_CREATED,
)
async def set_schedule_route(
    court_id: int,
    schedule_in: CourtScheduleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Set or update the opening and closing hours for a court on a specific day.

    The system will automatically generate 30-minute intervals between these times.

    Request Body:
        - day_of_week: Day of week (0=Monday, 6=Sunday)
        - opening_time: Opening time (e.g., "09:00") or null if closed
        - closing_time: Closing time (e.g., "21:00") or null if closed

    To mark a court as closed on a day, set both opening_time and closing_time to null.

    Requires admin role.
    """
    # Validate that both times are provided or both are None
    if (schedule_in.opening_time is None) != (schedule_in.closing_time is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both opening_time and closing_time must be provided together, or both omitted",
        )

    if (
        schedule_in.opening_time
        and schedule_in.closing_time
        and schedule_in.opening_time >= schedule_in.closing_time
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opening time must be before closing time",
        )

    schedule = await set_court_schedule(
        db, court_id, schedule_in.day_of_week, schedule_in.opening_time, schedule_in.closing_time
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )

    return schedule


@router.get("/{court_id}/schedule", response_model=list[CourtScheduleRead])
async def get_schedule_route(
    court_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Get the weekly schedule (opening/closing hours) for a court.

    Returns the schedule for all 7 days of the week (0=Monday, 6=Sunday).
    Days with NULL opening_time/closing_time are closed.

    Requires authentication.
    """
    # Check if court exists
    court = await get_court_by_id(db, court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )

    schedule = await get_court_schedule(db, court_id)
    return [CourtScheduleRead.model_validate(s) for s in schedule]


@router.get("/{court_id}/available-slots", response_model=AvailableSlotsResponse)
async def get_available_slots_route(
    court_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    slot_date: Annotated[
        date, Query(..., description="Date for which to retrieve available slots (YYYY-MM-DD)")
    ],
):
    """Get available 30-minute slots for a court on a specific date.

    If slots haven't been generated yet for this date, they will be automatically
    created based on the court's weekly schedule.

    Query Parameters:
        - slot_date: Date for which to retrieve slots (format: YYYY-MM-DD)

    Returns:
        List of available 30-minute slots with start and end times

    Requires authentication.
    """
    # Check if court exists
    court = await get_court_by_id(db, court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={court_id} not found",
        )

    # Get available slots (auto-generates if needed)
    available_slots = await get_available_slots(db, court_id, slot_date)

    return AvailableSlotsResponse(
        court_id=court_id,
        slot_date=slot_date,
        available_slots=[BookingSlotRead.model_validate(slot) for slot in available_slots],
        total_slots=len(available_slots),
    )
