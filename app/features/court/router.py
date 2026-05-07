from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.auth.dependencies import admin_guard, get_current_active_user
from app.features.user.models import User

from .schemas import CourtCreate, CourtRead, PaginatedCourtRead, CourtUpdate
from .service import create_court, delete_court_by_id, get_court_by_id, get_courts, update_court

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


@router.put("/{court_id}", response_model=CourtRead, status_code=status.HTTP_200_OK)
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


@router.delete("/{court_id}", status_code=status.HTTP_204_NO_CONTENT)
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
    return None
