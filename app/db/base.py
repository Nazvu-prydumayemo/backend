from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import your models here so Alembic can find them:
from app.features.user.models import User  # noqa: E402, F401
