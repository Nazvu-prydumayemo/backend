from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Court
from .schemas import CourtCreate, CourtUpdate


async def get_courts(db: AsyncSession) -> Sequence[Court]:
    """Retrieve all courts from the database."""
    result = await db.execute(select(Court))
    return result.scalars().all()


async def get_court_by_id(db: AsyncSession, court_id: int) -> Court | None:
    """Retrieve a court by its ID. Returns None if not found."""
    query = select(Court).where(Court.id == court_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_court(db: AsyncSession, data: CourtCreate) -> Court:
    """Create a new court with the provided data."""
    new_court = Court(
        number=data.number,
        surface_type=data.surface_type,
        is_indoor=data.is_indoor,
        price_per_hour=data.price_per_hour,
    )

    db.add(new_court)
    await db.commit()
    await db.refresh(new_court)

    return new_court


async def update_court(db: AsyncSession, court_id: int, data: CourtUpdate) -> Court | None:
    """Update an existing court with the provided data. Only updates provided fields."""
    court = await get_court_by_id(db, court_id)

    if not court:
        return None

    update_data = data.model_dump(exclude_unset=True)

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

