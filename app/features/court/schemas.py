from pydantic import BaseModel
from pydantic import ConfigDict
from datetime import datetime


class CourtBase(BaseModel):
    """Base schema for Court with common fields used in creation and reading."""
    surface_type: str
    is_indoor: bool
    price_per_hour: float
    description: str | None = None
    location: str | None = None


class CourtCreate(CourtBase):
    """Schema for creating a new Court. Inherits all fields from CourtBase."""


class CourtUpdate(BaseModel):
    """Schema for updating an existing Court. All fields are optional."""
    surface_type: str | None = None
    is_indoor: bool | None = None
    price_per_hour: float | None = None
    description: str | None = None
    location: str | None = None


class CourtRead(CourtBase):
    """Schema for reading Court data from the database."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True) 
