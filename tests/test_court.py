import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_court():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "surface_type": "clay",
            "is_indoor": False,
            "price_per_hour": 50.0
        }

        response = await ac.post("/api/v1/courts/", json=payload)
        assert response.status_code == 201
        data = response.json()
        # 'number' field removed; only check other fields
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


@pytest.mark.asyncio
async def test_get_court_by_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "surface_type": "hard",
            "is_indoor": True,
            "price_per_hour": 75.0,
        }

        create_response = await ac.post("/api/v1/courts/", json=payload)
        assert create_response.status_code == 201
        created_court = create_response.json()

        response = await ac.get(f"/api/v1/courts/{created_court['id']}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == created_court["id"]
        assert data["surface_type"] == payload["surface_type"]
        assert data["is_indoor"] == payload["is_indoor"]
        assert data["price_per_hour"] == payload["price_per_hour"]
        assert "created_at" in data


@pytest.mark.asyncio
async def test_get_court_by_id_returns_404_for_missing_court():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/courts/999999")

        assert response.status_code == 404
        assert response.json() == {"detail": "Court with id=999999 not found"}
