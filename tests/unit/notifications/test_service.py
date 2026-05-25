"""Unit tests for notifications service layer."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.features.notifications.service import send_booking_confirmation


class TestSendBookingConfirmation:
    """Tests for send_booking_confirmation function."""

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_success(self):
        """Should send booking confirmation email successfully."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(return_value=True)

            result = await send_booking_confirmation(
                recipient_email="user@example.com",
                user_name="John Doe",
                court_name="Tennis Court 1",
                booking_date=date(2026, 5, 26),
                time_slots="10:00 - 11:00",
                total_price=Decimal("50.00"),
            )

            assert result is True
            mock_service.send_booking_confirmation.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_failure(self):
        """Should return False on email service failure."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(return_value=False)

            result = await send_booking_confirmation(
                recipient_email="user@example.com",
                user_name="Jane Smith",
                court_name="Tennis Court 2",
                booking_date=date(2026, 5, 27),
                time_slots="14:00 - 15:00",
                total_price=Decimal("60.00"),
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_exception(self):
        """Should return False on exception."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await send_booking_confirmation(
                recipient_email="user@example.com",
                user_name="Bob Jones",
                court_name="Tennis Court 3",
                booking_date=date(2026, 5, 28),
                time_slots="16:00 - 17:00",
                total_price=Decimal("70.00"),
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_formats_date(self):
        """Should format date as ISO string."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(return_value=True)

            booking_date = date(2026, 6, 15)

            await send_booking_confirmation(
                recipient_email="user@example.com",
                user_name="Carol King",
                court_name="Tennis Court 4",
                booking_date=booking_date,
                time_slots="18:00 - 19:00",
                total_price=Decimal("80.00"),
            )

            # Check that ISO format date was passed
            call_args = mock_service.send_booking_confirmation.call_args
            assert call_args[1]["booking_date"] == "2026-06-15"

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_formats_price(self):
        """Should format price as string."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(return_value=True)

            total_price = Decimal("99.99")

            await send_booking_confirmation(
                recipient_email="user@example.com",
                user_name="Dave Grohl",
                court_name="Tennis Court 5",
                booking_date=date(2026, 6, 16),
                time_slots="20:00 - 21:00",
                total_price=total_price,
            )

            # Check that price was passed as string
            call_args = mock_service.send_booking_confirmation.call_args
            assert call_args[1]["total_price"] == "99.99"

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_passes_all_fields(self):
        """Should pass all fields to email service."""
        with patch("app.features.notifications.service.email_service") as mock_service:
            mock_service.send_booking_confirmation = AsyncMock(return_value=True)

            await send_booking_confirmation(
                recipient_email="eve@example.com",
                user_name="Eve Evans",
                court_name="Premium Court",
                booking_date=date(2026, 6, 17),
                time_slots="09:00 - 12:00",
                total_price=Decimal("150.00"),
            )

            call_args = mock_service.send_booking_confirmation.call_args
            assert call_args[1]["user_name"] == "Eve Evans"
            assert call_args[1]["court_name"] == "Premium Court"
            assert call_args[1]["time_slots"] == "09:00 - 12:00"
