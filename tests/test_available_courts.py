import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_available_courts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/courts/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for court in data:
            assert "id" in court
            assert "number" in court
            assert "surface_type" in court
            assert "is_indoor" in court
            assert "price_per_hour" in court
            assert "created_at" in court
