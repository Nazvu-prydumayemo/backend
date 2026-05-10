from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order
from .schemas import OrderCreate


async def create_order(db: AsyncSession, user_id: int, data: OrderCreate) -> Order:
    """Create a new order for the current user."""
    new_order = Order(user_id=user_id, court_id=data.court_id)

    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order


async def get_orders_by_user_id(db: AsyncSession, user_id: int) -> Sequence[Order]:
    """Retrieve all orders belonging to a specific user."""
    query = select(Order).where(Order.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_order_by_id(db: AsyncSession, order_id: int) -> Order | None:
    """Retrieve an order by its ID. Returns None if not found."""
    query = select(Order).where(Order.id == order_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()
