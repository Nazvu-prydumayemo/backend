import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.features.court.models import Court
from app.features.user.models import User
from app.main import app


async def create_user_and_token() -> tuple[User, str]:
    unique = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as db:
        user = User(
            firstname="Order",
            lastname="User",
            email=f"order-{unique}@example.com",
            password="unused",
            role_id=3,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return user, token


async def create_court() -> Court:
    unique = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as db:
        court = Court(
            name=f"Court-{unique}",
            surface_type="clay",
            is_indoor=False,
            price_per_hour=50.0,
            description="Order test court",
            location="North side",
        )
        db.add(court)
        await db.commit()
        await db.refresh(court)

    return court


@pytest.mark.asyncio
async def test_create_order():
    user, token = await create_user_and_token()
    court = await create_court()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/orders/",
            json={"court_id": court.id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user.id
    assert data["court_id"] == court.id
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_order_returns_404_for_missing_court():
    _, token = await create_user_and_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/orders/",
            json={"court_id": 999999},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Court with id=999999 not found"}


@pytest.mark.asyncio
async def test_get_orders_returns_current_users_orders_only():
    user, token = await create_user_and_token()
    other_user, other_token = await create_user_and_token()
    court_one = await create_court()
    court_two = await create_court()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_first = await ac.post(
            "/api/v1/orders/",
            json={"court_id": court_one.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        create_second = await ac.post(
            "/api/v1/orders/",
            json={"court_id": court_two.id},
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert create_first.status_code == 201
        assert create_second.status_code == 201

        response = await ac.get(
            "/api/v1/orders/",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["user_id"] == user.id
    assert data[0]["court_id"] == court_one.id
    assert data[0]["user_id"] != other_user.id


@pytest.mark.asyncio
async def test_get_order_by_id():
    user, token = await create_user_and_token()
    court = await create_court()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/v1/orders/",
            json={"court_id": court.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 201

        created_order = create_response.json()

        response = await ac.get(
            f"/api/v1/orders/{created_order['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_order["id"]
    assert data["user_id"] == user.id
    assert data["court_id"] == court.id


@pytest.mark.asyncio
async def test_get_order_by_id_returns_404_for_another_users_order():
    _, token = await create_user_and_token()
    _, other_token = await create_user_and_token()
    court = await create_court()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/v1/orders/",
            json={"court_id": court.id},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert create_response.status_code == 201

        created_order = create_response.json()

        response = await ac.get(
            f"/api/v1/orders/{created_order['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": f"Order with id={created_order['id']} not found"}


@pytest.mark.asyncio
async def test_get_order_by_id_returns_404_for_missing_order():
    _, token = await create_user_and_token()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/orders/999999",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Order with id=999999 not found"}
