"""Pytest configuration with Testcontainers PostgreSQL (fallback to SQLite)."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from app.core.database import get_db
from app.db.base import Base
from app.main import app as fastapi_app

# Windows event loop compatibility for asyncpg
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def db_engine_type():
    """Determine which database engine we're using."""
    try:
        container = PostgresContainer(
            image="postgres:16-alpine",
            driver="asyncpg",
            dbname="test_db",
            username="test_user",
            password="test_password",
        )
        container.start()
        container.stop()
        return "postgresql"
    except Exception:
        return "sqlite"


@pytest.fixture(scope="session")
async def postgres_engine_session(db_engine_type):
    """Session-scoped PostgreSQL engine (only created if Docker available)."""
    if db_engine_type != "postgresql":
        yield None
        return

    container = PostgresContainer(
        image="postgres:16-alpine",
        driver="asyncpg",
        dbname="test_db",
        username="test_user",
        password="test_password",
    )
    container.start()
    test_db_url = container.get_connection_url().replace("+psycopg", "+asyncpg")
    engine = create_async_engine(test_db_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text("""
                INSERT INTO user_roles (id, name)
                VALUES (1, 'admin'), (2, 'moderator'), (3, 'user')
                ON CONFLICT (id) DO NOTHING
            """)
        )

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    container.stop()


@pytest.fixture
async def test_engine(db_engine_type, postgres_engine_session):
    """Create per-test database engine."""
    if db_engine_type == "postgresql":
        yield postgres_engine_session
    else:
        # Create fresh SQLite in-memory database for each test
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(
                    text("""
                        INSERT INTO user_roles (id, name)
                        VALUES (1, 'admin'), (2, 'moderator'), (3, 'user')
                    """)
                )
            except Exception:
                pass

        yield engine

        # Cleanup
        await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Provide test database session with rollback isolation."""
    factory = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    async with factory() as session:
        dialect_name = test_engine.dialect.name

        if dialect_name == "sqlite":
            # SQLite: fresh database per test, no nested transaction needed
            yield session
        else:
            # PostgreSQL: use nested transactions for isolation
            async with session.begin_nested():
                yield session


@pytest.fixture
async def client(db_session):
    """FastAPI TestClient with test database dependency override."""
    fastapi_app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
