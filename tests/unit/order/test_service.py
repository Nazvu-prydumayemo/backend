"""Unit tests for order service layer."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.court.models import BookingSlot
from app.features.court.schemas import CourtCreate
from app.features.court.service import create_court
from app.features.order.schemas import OrderCreate
from app.features.order.service import (
    OrderValidationError,
    create_order,
    create_order_with_slots,
    format_slot_ranges,
    get_order_by_id,
    get_orders_by_user_id,
)
from app.features.user.schemas import UserCreate, UserRoleEnum
from app.features.user.service import create_user


class TestCreateOrder:
    """Tests for create_order function."""

    async def test_create_order_success(self, db_session: AsyncSession):
        """Should create a basic order."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 1",
                surface_type="Clay",
                is_indoor=False,
                location="Location 1",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        order = await create_order(
            db_session, user.id, OrderCreate(court_id=court.id, booking_slot_ids=[])
        )

        assert order is not None
        assert order.user_id == user.id
        assert order.court_id == court.id


class TestCreateOrderWithSlots:
    """Tests for create_order_with_slots function."""

    async def test_create_order_with_slots_success(self, db_session: AsyncSession):
        """Should create order with slots and mark them unavailable."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Jane",
                lastname="Smith",
                email="jane@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 2",
                surface_type="Clay",
                is_indoor=False,
                location="Location 2",
                price_per_hour=float(Decimal("60.00")),
            ),
        )

        # Create booking slots
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
        slot1 = BookingSlot(
            court_id=court.id,
            slot_date=tomorrow,
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
            is_available=True,
        )
        slot2 = BookingSlot(
            court_id=court.id,
            slot_date=tomorrow,
            start_time=datetime.strptime("10:30", "%H:%M").time(),
            end_time=datetime.strptime("11:00", "%H:%M").time(),
            is_available=True,
        )
        db_session.add(slot1)
        db_session.add(slot2)
        await db_session.commit()
        await db_session.refresh(slot1)
        await db_session.refresh(slot2)

        order = await create_order_with_slots(db_session, user.id, court.id, [slot1.id, slot2.id])

        assert order is not None
        assert order.user_id == user.id
        assert len(order.booking_slots) == 2
        assert order.total_price == float(Decimal("60.00"))  # 2 slots * 0.5 hours each

    async def test_create_order_with_slots_missing_slot(self, db_session: AsyncSession):
        """Should raise OrderValidationError if slot doesn't exist."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Bob",
                lastname="Jones",
                email="bob@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 3",
                surface_type="Clay",
                is_indoor=False,
                location="Location 3",
                price_per_hour=float(Decimal("70.00")),
            ),
        )

        with pytest.raises(OrderValidationError) as exc_info:
            await create_order_with_slots(db_session, user.id, court.id, [99999])

        assert "not found" in exc_info.value.message.lower()

    async def test_create_order_with_slots_wrong_court(self, db_session: AsyncSession):
        """Should raise OrderValidationError if slots don't belong to court."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Carol",
                lastname="King",
                email="carol@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court1 = await create_court(
            db_session,
            CourtCreate(
                name="Court 4",
                surface_type="Clay",
                is_indoor=False,
                location="Location 4",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        court2 = await create_court(
            db_session,
            CourtCreate(
                name="Court 5",
                surface_type="Clay",
                is_indoor=False,
                location="Location 5",
                price_per_hour=float(Decimal("60.00")),
            ),
        )

        # Create slot for court1
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
        slot = BookingSlot(
            court_id=court1.id,
            slot_date=tomorrow,
            start_time=datetime.strptime("12:00", "%H:%M").time(),
            end_time=datetime.strptime("12:30", "%H:%M").time(),
            is_available=True,
        )
        db_session.add(slot)
        await db_session.commit()
        await db_session.refresh(slot)

        # Try to create order with court2
        with pytest.raises(OrderValidationError) as exc_info:
            await create_order_with_slots(db_session, user.id, court2.id, [slot.id])

        assert "do not belong to court" in exc_info.value.message.lower()

    async def test_create_order_with_slots_unavailable(self, db_session: AsyncSession):
        """Should raise OrderValidationError if slots are unavailable."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Dave",
                lastname="Grohl",
                email="dave@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 6",
                surface_type="Clay",
                is_indoor=False,
                location="Location 6",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
        slot = BookingSlot(
            court_id=court.id,
            slot_date=tomorrow,
            start_time=datetime.strptime("14:00", "%H:%M").time(),
            end_time=datetime.strptime("14:30", "%H:%M").time(),
            is_available=False,  # Already booked
        )
        db_session.add(slot)
        await db_session.commit()
        await db_session.refresh(slot)

        with pytest.raises(OrderValidationError) as exc_info:
            await create_order_with_slots(db_session, user.id, court.id, [slot.id])

        assert "not available" in exc_info.value.message.lower()

    async def test_create_order_with_slots_out_of_range_future(self, db_session: AsyncSession):
        """Should raise OrderValidationError if slot is more than 7 days away."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Eve",
                lastname="Evans",
                email="eve@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 7",
                surface_type="Clay",
                is_indoor=False,
                location="Location 7",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Slot 10 days in the future (beyond +7 day window)
        future_date = (datetime.now(UTC) + timedelta(days=10)).date()
        slot = BookingSlot(
            court_id=court.id,
            slot_date=future_date,
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
            is_available=True,
        )
        db_session.add(slot)
        await db_session.commit()
        await db_session.refresh(slot)

        with pytest.raises(OrderValidationError) as exc_info:
            await create_order_with_slots(db_session, user.id, court.id, [slot.id])

        assert "outside the allowed" in exc_info.value.message.lower()

    async def test_create_order_with_slots_past_time_today(self, db_session: AsyncSession):
        """Should raise OrderValidationError if slot time has already passed."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Frank",
                lastname="Sinatra",
                email="frank@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 8",
                surface_type="Clay",
                is_indoor=False,
                location="Location 8",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Slot with past time (1 hour ago)
        today = datetime.now(UTC).date()
        past_time = (datetime.now(UTC) - timedelta(hours=1)).time()
        slot = BookingSlot(
            court_id=court.id,
            slot_date=today,
            start_time=past_time,
            end_time=datetime.strptime("23:59", "%H:%M").time(),
            is_available=True,
        )
        db_session.add(slot)
        await db_session.commit()
        await db_session.refresh(slot)

        with pytest.raises(OrderValidationError) as exc_info:
            await create_order_with_slots(db_session, user.id, court.id, [slot.id])

        assert "already passed" in exc_info.value.message.lower()


class TestFormatSlotRanges:
    """Tests for format_slot_ranges function."""

    def test_format_slot_ranges_single(self):
        """Should format single slot."""
        slot = BookingSlot(
            court_id=1,
            slot_date=date.today(),
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
            is_available=True,
        )

        result = format_slot_ranges([slot])
        assert result == "10:00 - 10:30"

    def test_format_slot_ranges_consecutive(self):
        """Should merge consecutive slots into range."""
        slot1 = BookingSlot(
            court_id=1,
            slot_date=date.today(),
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
            is_available=True,
        )
        slot2 = BookingSlot(
            court_id=1,
            slot_date=date.today(),
            start_time=datetime.strptime("10:30", "%H:%M").time(),
            end_time=datetime.strptime("11:00", "%H:%M").time(),
            is_available=True,
        )

        result = format_slot_ranges([slot1, slot2])
        assert result == "10:00 - 11:00"

    def test_format_slot_ranges_separate(self):
        """Should show separate ranges for non-consecutive slots."""
        slot1 = BookingSlot(
            court_id=1,
            slot_date=date.today(),
            start_time=datetime.strptime("10:00", "%H:%M").time(),
            end_time=datetime.strptime("10:30", "%H:%M").time(),
            is_available=True,
        )
        slot2 = BookingSlot(
            court_id=1,
            slot_date=date.today(),
            start_time=datetime.strptime("14:00", "%H:%M").time(),
            end_time=datetime.strptime("14:30", "%H:%M").time(),
            is_available=True,
        )

        result = format_slot_ranges([slot1, slot2])
        assert "10:00 - 10:30" in result
        assert "14:00 - 14:30" in result


class TestGetOrdersById:
    """Tests for get_orders_by_user_id function."""

    async def test_get_orders_by_user_id_empty(self, db_session: AsyncSession):
        """Should return empty sequence when user has no orders."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Grace",
                lastname="Hopper",
                email="grace@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        orders = await get_orders_by_user_id(db_session, user.id)
        assert len(orders) == 0

    async def test_get_orders_by_user_id_multiple(self, db_session: AsyncSession):
        """Should retrieve all orders for a user."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Henry",
                lastname="Ford",
                email="henry@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 9",
                surface_type="Clay",
                is_indoor=False,
                location="Location 9",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Create multiple orders
        await create_order(db_session, user.id, OrderCreate(court_id=court.id, booking_slot_ids=[]))
        await create_order(db_session, user.id, OrderCreate(court_id=court.id, booking_slot_ids=[]))

        orders = await get_orders_by_user_id(db_session, user.id)
        assert len(orders) >= 2


class TestGetOrderById:
    """Tests for get_order_by_id function."""

    async def test_get_order_by_id_success(self, db_session: AsyncSession):
        """Should retrieve order by ID."""
        user = await create_user(
            db_session,
            UserCreate(
                firstname="Iris",
                lastname="West",
                email="iris@example.com",
                password="Pass123!",
                role_id=UserRoleEnum.USER,
            ),
        )
        assert user is not None

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 10",
                surface_type="Clay",
                is_indoor=False,
                location="Location 10",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        order = await create_order(
            db_session, user.id, OrderCreate(court_id=court.id, booking_slot_ids=[])
        )

        found = await get_order_by_id(db_session, order.id)
        assert found is not None
        assert found.id == order.id

    async def test_get_order_by_id_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent order."""
        result = await get_order_by_id(db_session, 99999)
        assert result is None
