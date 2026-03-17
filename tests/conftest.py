import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base
import app.features.court.models  # noqa: F401 — щоб Base.metadata побачила таблицю courts


@pytest.fixture(autouse=True, scope="session")
async def prepare_database():
    """Create all tables before tests and drop them after."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
