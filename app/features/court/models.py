from sqlalchemy import Boolean, String, Float, DateTime
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, init=False)

    number: Mapped[int] = mapped_column(nullable=False)

    surface_type: Mapped[str] = mapped_column(String, nullable=False)

    price_per_hour: Mapped[float] = mapped_column(Float, nullable=False)

    is_indoor: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), init=False)