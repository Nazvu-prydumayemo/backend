from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import get_current_active_user
from app.features.court.service import get_court_by_id
from app.features.user.models import User

from .schemas import OrderCreate, OrderRead
from .service import create_order, get_order_by_id, get_orders_by_user_id

router = APIRouter(prefix="/orders", tags=["Orders"])

AUTH_RESPONSES = {
    401: {"description": "Unauthorized - Invalid or missing authentication token"},
    403: {"description": "Forbidden - User account is inactive"},
}


@router.post(
    "/",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTH_RESPONSES,
        404: {"description": "Court not found"},
        422: {"description": "Validation error - Invalid input data"},
    },
)
async def create_order_route(
    order_in: OrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Create a new court order for the current authenticated user."""
    court = await get_court_by_id(db, order_in.court_id)
    if not court:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court with id={order_in.court_id} not found",
        )

    return await create_order(db, current_user.id, order_in)


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
    response_model=OrderRead,
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
