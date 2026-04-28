from sqlalchemy import Boolean, DateTime, Float, String, Text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    name: Mapped[str] = mapped_column(String, nullable=False)

    surface_type: Mapped[str] = mapped_column(String, nullable=False)

    price_per_hour: Mapped[float] = mapped_column(Float, nullable=False)

    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    location: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    working_hours: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), init=False)
