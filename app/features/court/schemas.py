from pydantic import BaseModel


class CourtBase(BaseModel):
    """Base schema for Court with common fields used in creation and reading."""
    number: int
    surface_type: str
    is_indoor: bool
    price_per_hour: float


class CourtCreate(CourtBase):
    """Schema for creating a new Court. Inherits all fields from CourtBase."""


class CourtUpdate(BaseModel):
    """Schema for updating an existing Court. All fields are optional."""
    number: int | None = None
    surface_type: str | None = None
    is_indoor: bool | None = None
    price_per_hour: float | None = None


class CourtRead(CourtBase):
    """Schema for reading Court data from the database."""
    id: int
    created_at: str  # Or use datetime if needed

    class Config:
        from_attributes = True