import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email_with_different_case():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        first_payload = {
            "firstname": "Test",
            "lastname": "User",
            "email": "Test@gmail.com",
            "password": "secret123",
        }
        second_payload = {
            "firstname": "Another",
            "lastname": "User",
            "email": "test@gmail.com",
            "password": "secret123",
        }

        first_response = await ac.post("/api/v1/auth/register", json=first_payload)
        assert first_response.status_code == 201

        second_response = await ac.post("/api/v1/auth/register", json=second_payload)
        assert second_response.status_code == 400
        assert second_response.json() == {"detail": "Email already registered"}


@pytest.mark.asyncio
async def test_login_accepts_email_with_different_case():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        register_payload = {
            "firstname": "Login",
            "lastname": "Case",
            "email": "TestLogin@gmail.com",
            "password": "secret123",
        }

        register_response = await ac.post("/api/v1/auth/register", json=register_payload)
        assert register_response.status_code == 201

        login_response = await ac.post(
            "/api/v1/auth/login",
            json={"email": "testlogin@gmail.com", "password": "secret123"},
        )
        assert login_response.status_code == 200

        data = login_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
