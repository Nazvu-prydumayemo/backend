from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from .schemas import CourtCreate, CourtRead, CourtUpdate
from .service import create_court, get_courts

router = APIRouter(prefix="/courts", tags=["Courts"])

@router.post("/", response_model=CourtRead, status_code=status.HTTP_201_CREATED)
async def create_court_route(
    court_in: CourtCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new court entry."""
    return await create_court(db, court_in)


@router.get("/", response_model=list[CourtRead], status_code=status.HTTP_200_OK)
async def get_courts_route(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all available courts."""
    return await get_courts(db)