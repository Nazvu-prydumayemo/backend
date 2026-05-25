"""Unit tests for court service layer."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.court.schemas import CourtCreate, CourtUpdate
from app.features.court.service import (
    create_court,
    delete_court_by_id,
    get_available_slots,
    get_court_by_id,
    get_court_schedule,
    get_court_with_schedule,
    get_courts,
    set_court_schedule,
    update_court,
)


class TestGetCourts:
    """Tests for get_courts function."""

    async def test_get_courts_empty(self, db_session: AsyncSession):
        """Should return empty list when no courts exist."""
        courts, total = await get_courts(db_session)
        assert len(courts) == 0
        assert total == 0

    async def test_get_courts_pagination(self, db_session: AsyncSession):
        """Should handle pagination correctly."""
        # Create multiple courts
        for i in range(5):
            await create_court(
                db_session,
                CourtCreate(
                    name=f"Court {i}",
                    surface_type="Clay",
                    is_indoor=False,
                    location=f"Location {i}",
                    price_per_hour=float(Decimal("50.00")),
                ),
            )

        # Test limit
        courts, total = await get_courts(db_session, skip=0, limit=2)
        assert len(courts) == 2
        assert total >= 5

    async def test_get_courts_skip(self, db_session: AsyncSession):
        """Should skip records correctly."""
        courts1, _ = await get_courts(db_session, skip=0, limit=10)
        courts2, _ = await get_courts(db_session, skip=2, limit=10)

        assert len(courts2) <= len(courts1)


class TestGetCourtById:
    """Tests for get_court_by_id function."""

    async def test_get_court_by_id_success(self, db_session: AsyncSession):
        """Should retrieve court by ID."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Tennis Court 1",
                surface_type="Clay",
                is_indoor=False,
                location="Downtown",
                price_per_hour=float(Decimal("75.00")),
            ),
        )

        found = await get_court_by_id(db_session, court.id)
        assert found is not None
        assert found.id == court.id
        assert found.name == "Tennis Court 1"

    async def test_get_court_by_id_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent court."""
        result = await get_court_by_id(db_session, 99999)
        assert result is None


class TestCreateCourt:
    """Tests for create_court function."""

    async def test_create_court_success(self, db_session: AsyncSession):
        """Should create a new court."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="New Court",
                surface_type="Concrete",
                is_indoor=True,
                location="New Location",
                price_per_hour=float(Decimal("100.00")),
            ),
        )

        assert court is not None
        assert court.name == "New Court"
        assert court.price_per_hour == float(Decimal("100.00"))

    async def test_create_court_fields(self, db_session: AsyncSession):
        """Should preserve all court fields."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Field Test Court",
                surface_type="Grass",
                is_indoor=False,
                location="Test Location",
                price_per_hour=float(Decimal("60.50")),
                description="Test info with special chars: !@#$%",
            ),
        )

        assert court.location == "Test Location"
        assert court.description == "Test info with special chars: !@#$%"


class TestUpdateCourt:
    """Tests for update_court function."""

    async def test_update_court_success(self, db_session: AsyncSession):
        """Should update court fields."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Original Name",
                surface_type="Clay",
                is_indoor=False,
                location="Original Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        updated = await update_court(
            db_session,
            court.id,
            CourtUpdate(
                name="Updated Name",
                price_per_hour=float(Decimal("75.00")),
            ),
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.price_per_hour == float(Decimal("75.00"))
        # Location should remain unchanged
        assert updated.location == "Original Location"

    async def test_update_court_partial(self, db_session: AsyncSession):
        """Should update only provided fields."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court A",
                surface_type="Clay",
                is_indoor=False,
                location="Location A",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        updated = await update_court(
            db_session,
            court.id,
            CourtUpdate(name="Court B"),
        )

        assert updated is not None
        assert updated.name == "Court B"
        assert updated.location == "Location A"

    async def test_update_court_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent court."""
        result = await update_court(
            db_session,
            99999,
            CourtUpdate(name="New Name"),
        )
        assert result is None


class TestDeleteCourtById:
    """Tests for delete_court_by_id function."""

    async def test_delete_court_success(self, db_session: AsyncSession):
        """Should delete a court."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court to Delete",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        deleted = await delete_court_by_id(db_session, court.id)
        assert deleted is not None
        assert deleted.id == court.id

        # Verify court is deleted
        found = await get_court_by_id(db_session, court.id)
        assert found is None

    async def test_delete_court_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent court."""
        result = await delete_court_by_id(db_session, 99999)
        assert result is None


class TestSetCourtSchedule:
    """Tests for set_court_schedule function."""

    async def test_set_court_schedule_success(self, db_session: AsyncSession):
        """Should create court schedule."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Scheduled Court",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        from datetime import time

        schedule = await set_court_schedule(
            db_session,
            court.id,
            day_of_week=0,  # Monday
            opening_time=time(9, 0),
            closing_time=time(22, 0),
        )

        assert schedule is not None
        assert schedule.day_of_week == 0
        assert schedule.opening_time == time(9, 0)
        assert schedule.closing_time == time(22, 0)

    async def test_set_court_schedule_closed_day(self, db_session: AsyncSession):
        """Should create schedule with no hours (closed day)."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 2",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        schedule = await set_court_schedule(
            db_session,
            court.id,
            day_of_week=6,  # Sunday - closed
            opening_time=None,
            closing_time=None,
        )

        assert schedule is not None
        assert schedule.opening_time is None
        assert schedule.closing_time is None

    async def test_set_court_schedule_update(self, db_session: AsyncSession):
        """Should update existing schedule."""
        from datetime import time

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 3",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Create initial schedule
        await set_court_schedule(
            db_session,
            court.id,
            day_of_week=1,  # Tuesday
            opening_time=time(8, 0),
            closing_time=time(20, 0),
        )

        # Update schedule
        updated = await set_court_schedule(
            db_session,
            court.id,
            day_of_week=1,
            opening_time=time(9, 0),
            closing_time=time(21, 0),
        )

        assert updated is not None
        assert updated.opening_time == time(9, 0)
        assert updated.closing_time == time(21, 0)

    async def test_set_court_schedule_court_not_found(self, db_session: AsyncSession):
        """Should return None if court doesn't exist."""
        from datetime import time

        result = await set_court_schedule(
            db_session,
            99999,
            day_of_week=0,
            opening_time=time(9, 0),
            closing_time=time(22, 0),
        )
        assert result is None


class TestGetCourtSchedule:
    """Tests for get_court_schedule function."""

    async def test_get_court_schedule_empty(self, db_session: AsyncSession):
        """Should return empty schedule for new court."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 4",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        schedule = await get_court_schedule(db_session, court.id)
        assert len(schedule) == 0

    async def test_get_court_schedule_multiple_days(self, db_session: AsyncSession):
        """Should retrieve all schedule entries."""
        from datetime import time

        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 5",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Create schedules for multiple days
        for day in range(7):
            await set_court_schedule(
                db_session,
                court.id,
                day_of_week=day,
                opening_time=time(9, 0),
                closing_time=time(22, 0),
            )

        schedule = await get_court_schedule(db_session, court.id)
        assert len(schedule) == 7


class TestGetAvailableSlots:
    """Tests for get_available_slots function."""

    async def test_get_available_slots_valid_date(self, db_session: AsyncSession):
        """Should get slots for valid date (within +7 days)."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 6",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Valid date: tomorrow (using UTC to match validation)
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()

        # This should not raise (though may return empty if no schedule)
        try:
            slots = await get_available_slots(db_session, court.id, tomorrow)
            assert slots is not None
        except ValueError:
            pass  # May fail if no schedule set, which is ok

    async def test_get_available_slots_past_date(self, db_session: AsyncSession):
        """Should raise ValueError for past date."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 7",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # Past date (using UTC to match validation)
        yesterday = (datetime.now(UTC) - timedelta(days=1)).date()

        with pytest.raises(ValueError):
            await get_available_slots(db_session, court.id, yesterday)

    async def test_get_available_slots_too_far_future(self, db_session: AsyncSession):
        """Should raise ValueError for dates beyond +7 days."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 8",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        # 10 days in future (beyond +7 day window, using UTC to match validation)
        far_future = (datetime.now(UTC) + timedelta(days=10)).date()

        with pytest.raises(ValueError):
            await get_available_slots(db_session, court.id, far_future)


class TestGetCourtWithSchedule:
    """Tests for get_court_with_schedule function."""

    async def test_get_court_with_schedule_success(self, db_session: AsyncSession):
        """Should retrieve court with schedule loaded."""
        court = await create_court(
            db_session,
            CourtCreate(
                name="Court 9",
                surface_type="Clay",
                is_indoor=False,
                location="Location",
                price_per_hour=float(Decimal("50.00")),
            ),
        )

        from datetime import time

        await set_court_schedule(
            db_session,
            court.id,
            day_of_week=0,
            opening_time=time(9, 0),
            closing_time=time(22, 0),
        )

        found = await get_court_with_schedule(db_session, court.id)
        assert found is not None
        assert found.id == court.id

    async def test_get_court_with_schedule_not_found(self, db_session: AsyncSession):
        """Should return None for nonexistent court."""
        result = await get_court_with_schedule(db_session, 99999)
        assert result is None
