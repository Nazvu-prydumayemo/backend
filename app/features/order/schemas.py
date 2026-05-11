from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrderCreate(BaseModel):
    court_id: int


class OrderRead(BaseModel):
    id: int
    user_id: int
    court_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
