from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import admin_guard, get_current_active_user
from app.features.user.models import User

from .schemas import CourtCreate, CourtRead
from .service import create_court, get_court_by_id, get_courts

router = APIRouter(prefix="/courts", tags=["Courts"])


@router.post("/", response_model=CourtRead, status_code=status.HTTP_201_CREATED)
async def create_court_route(
    court_in: CourtCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(admin_guard)],
):
    """Create a new court entry. Requires admin role."""
    return await create_court(db, court_in)


@router.get("/", response_model=list[CourtRead], status_code=status.HTTP_200_OK)
async def get_courts_route(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve all available courts. Requires authentication."""
    return await get_courts(db)


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
