import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_env_database_url(monkeypatch):
    # Check if the app loads the correct database URL from .env
    import app.core.config
    assert app.core.config.settings.DATABASE_URL == 'sqlite+aiosqlite:///./test.db'

@pytest.mark.asyncio
async def test_create_court():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "number": 1,
            "surface_type": "clay",
            "is_indoor": False,
            "price_per_hour": 50.0
        }

        response = await ac.post("/api/v1/courts/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["number"] == payload["number"]
        assert data["surface_type"] == payload["surface_type"]
        assert data["is_indoor"] == payload["is_indoor"]
        assert data["price_per_hour"] == payload["price_per_hour"]
        assert "id" in data
        assert "created_at" in data

@pytest.mark.asyncio
async def test_get_courts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/courts/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)