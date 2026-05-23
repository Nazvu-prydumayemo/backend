"""Pydantic model for health-check status response."""

from datetime import datetime

from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Schema for health-check status response with server timestamp."""

    status: str
    timestamp: datetime
