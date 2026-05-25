"""Order endpoints: create orders, list orders, retrieve order details."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import get_current_active_user
from app.features.court.service import get_court_by_id
from app.features.notifications.scheduler import schedule_reminder
from app.features.notifications.service import send_booking_confirmation
from app.features.user.models import User

from .schemas import OrderCreate, OrderDetailResponse, OrderRead
from .service import (
    OrderValidationError,
    create_order_with_slots,
    format_slot_ranges,
    get_order_by_id,
    get_orders_by_user_id,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Unauthorized - Invalid or missing authentication token"},
    403: {"description": "Forbidden - User account is inactive"},
}


@router.post(
    "/",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTH_RESPONSES,
        400: {"description": "Validation error - Booking slots not available"},
        404: {"description": "Court or booking slots not found"},
        422: {"description": "Validation error - Invalid input data"},
    },
)
async def create_order_route(
    order_in: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new court order with booking slots for the current authenticated user.

    The request should include a list of booking slot IDs that you want to book.
    All slots must be available, otherwise the entire order is rejected (all-or-nothing).
    """
    court = await get_court_by_id(db, order_in.court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={order_in.court_id} not found",
        )

    try:
        order = await create_order_with_slots(
            db,
            current_user.id,
            order_in.court_id,
            order_in.booking_slot_ids,
        )
    except OrderValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.message,
                "unavailable_slots": e.unavailable_slots,
            },
        ) from e

    # Send booking confirmation email in the background
    if order.booking_slots and order.booking_date is not None and order.total_price is not None:
        first_slot = order.booking_slots[0]
        time_slots = format_slot_ranges(order.booking_slots)
        background_tasks.add_task(
            send_booking_confirmation,
            current_user.email,
            current_user.firstname,
            court.name,
            order.booking_date,
            time_slots,
            order.total_price,
        )

        # Schedule reminder 1 hour before first slot
        first_slot_datetime = datetime.combine(
            first_slot.slot_date, first_slot.start_time, tzinfo=UTC
        )
        schedule_reminder(order.id, first_slot_datetime)

    return order


@router.get(
    "/",
    response_model=list[OrderRead],
    status_code=status.HTTP_200_OK,
    responses=AUTH_RESPONSES,
)
async def get_orders_route(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve all orders belonging to the current authenticated user."""
    return await get_orders_by_user_id(db, current_user.id)


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **AUTH_RESPONSES,
        404: {"description": "Order not found"},
    },
)
async def get_order_route(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve a specific order by ID for the current authenticated user."""
    order = await get_order_by_id(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id={order_id} not found",
        )

    return order
