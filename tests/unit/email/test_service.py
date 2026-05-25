"""Unit tests for email service layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi_mail import NameEmail

from app.features.email.service import EmailService


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_email_service_init(self):
        """Should initialize EmailService with config."""
        service = EmailService()
        assert service.config is not None
        assert service.fm is not None


class TestEmailServiceSendEmail:
    """Tests for send_email method."""

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Should return True on successful email send."""
        service = EmailService()

        # Mock FastMail.send_message
        service.fm.send_message = AsyncMock(return_value=None)

        result = await service.send_email(
            subject="Test",
            recipients=[NameEmail(email="test@example.com", name="Test")],
            body="Test body",
        )

        assert result is True
        service.fm.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_connection_error(self):
        """Should return False on connection error."""
        from fastapi_mail import errors

        service = EmailService()

        # Mock FastMail to raise ConnectionError
        service.fm.send_message = AsyncMock(side_effect=errors.ConnectionErrors("Failed"))

        result = await service.send_email(
            subject="Test",
            recipients=[NameEmail(email="test@example.com", name="Test")],
            body="Test body",
        )

        assert result is False


class TestEmailServiceWelcomeEmail:
    """Tests for send_welcome_email method."""

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(self):
        """Should send welcome email successfully."""
        service = EmailService()

        # Mock the send_email method
        service.send_email = AsyncMock(return_value=True)

        result = await service.send_welcome_email(
            NameEmail(email="newuser@example.com", name="New User"),
            "John Doe",
        )

        assert result is True
        service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_email_template_not_found(self):
        """Should return False if template not found."""
        service = EmailService()

        # Mock _load_template to raise FileNotFoundError
        service._load_template = MagicMock(side_effect=FileNotFoundError("Not found"))

        result = await service.send_welcome_email(
            NameEmail(email="newuser@example.com", name="New User"),
            "Jane Smith",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_welcome_email_connection_error(self):
        """Should return False on connection error."""
        from fastapi_mail import errors

        service = EmailService()

        # Mock send_email to raise ConnectionError
        service.send_email = AsyncMock(side_effect=errors.ConnectionErrors("Failed"))

        result = await service.send_welcome_email(
            NameEmail(email="newuser@example.com", name="New User"),
            "Bob Jones",
        )

        assert result is False


class TestEmailServiceResetPasswordEmail:
    """Tests for send_reset_password_email method."""

    @pytest.mark.asyncio
    async def test_send_reset_password_email_success(self):
        """Should send reset password email successfully."""
        service = EmailService()

        service.send_email = AsyncMock(return_value=True)

        result = await service.send_reset_password_email(
            NameEmail(email="user@example.com", name="User"),
            "Carol King",
            "123456",
        )

        assert result is True
        service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_reset_password_email_template_not_found(self):
        """Should return False if template not found."""
        service = EmailService()

        service._load_template = MagicMock(side_effect=FileNotFoundError("Not found"))

        result = await service.send_reset_password_email(
            NameEmail(email="user@example.com", name="User"),
            "Dave Smith",
            "654321",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_reset_password_email_connection_error(self):
        """Should return False on connection error."""
        from fastapi_mail import errors

        service = EmailService()

        service.send_email = AsyncMock(side_effect=errors.ConnectionErrors("Failed"))

        result = await service.send_reset_password_email(
            NameEmail(email="user@example.com", name="User"),
            "Eve Evans",
            "111111",
        )

        assert result is False


class TestEmailServiceBookingConfirmation:
    """Tests for send_booking_confirmation method."""

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_success(self):
        """Should send booking confirmation email successfully."""
        service = EmailService()

        service.send_email = AsyncMock(return_value=True)

        result = await service.send_booking_confirmation(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Frank Sinatra",
            court_name="Court A",
            booking_date="2026-05-26",
            time_slots="10:00 - 11:00",
            total_price="50.00",
        )

        assert result is True
        service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_template_not_found(self):
        """Should return False if template not found."""
        service = EmailService()

        service._load_template = MagicMock(side_effect=FileNotFoundError("Not found"))

        result = await service.send_booking_confirmation(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Grace Hopper",
            court_name="Court B",
            booking_date="2026-05-27",
            time_slots="14:00 - 15:00",
            total_price="60.00",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_booking_confirmation_connection_error(self):
        """Should return False on connection error."""
        from fastapi_mail import errors

        service = EmailService()

        service.send_email = AsyncMock(side_effect=errors.ConnectionErrors("Failed"))

        result = await service.send_booking_confirmation(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Henry Ford",
            court_name="Court C",
            booking_date="2026-05-28",
            time_slots="16:00 - 17:00",
            total_price="70.00",
        )

        assert result is False


class TestEmailServiceBookingReminder:
    """Tests for send_booking_reminder method."""

    @pytest.mark.asyncio
    async def test_send_booking_reminder_success(self):
        """Should send booking reminder email successfully."""
        service = EmailService()

        service.send_email = AsyncMock(return_value=True)

        result = await service.send_booking_reminder(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Iris West",
            court_name="Court D",
            booking_date="2026-05-29",
            time_slots="18:00 - 19:00",
            location="Downtown",
        )

        assert result is True
        service.send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_booking_reminder_template_not_found(self):
        """Should return False if template not found."""
        service = EmailService()

        service._load_template = MagicMock(side_effect=FileNotFoundError("Not found"))

        result = await service.send_booking_reminder(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Jack Johnson",
            court_name="Court E",
            booking_date="2026-05-30",
            time_slots="20:00 - 21:00",
            location="Uptown",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_booking_reminder_connection_error(self):
        """Should return False on connection error."""
        from fastapi_mail import errors

        service = EmailService()

        service.send_email = AsyncMock(side_effect=errors.ConnectionErrors("Failed"))

        result = await service.send_booking_reminder(
            recipient_email=NameEmail(email="user@example.com", name="User"),
            user_name="Kate Knight",
            court_name="Court F",
            booking_date="2026-05-31",
            time_slots="09:00 - 10:00",
            location="Midtown",
        )

        assert result is False


class TestEmailServiceLoadTemplate:
    """Tests for _load_template method."""

    def test_load_template_success(self):
        """Should load template file content."""
        service = EmailService()

        # Mock the TEMPLATES_DIR
        with patch("app.features.email.service.TEMPLATES_DIR") as mock_templates_dir:
            mock_path_instance = MagicMock()
            mock_templates_dir.__truediv__.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.read_text.return_value = "<html>Template</html>"

            result = service._load_template("test.html")
            assert result == "<html>Template</html>"

    def test_load_template_not_found(self):
        """Should raise FileNotFoundError for missing template."""
        service = EmailService()

        # Mock the TEMPLATES_DIR to return non-existent path
        with patch("app.features.email.service.TEMPLATES_DIR") as mock_templates_dir:
            mock_path_instance = MagicMock()
            mock_templates_dir.__truediv__.return_value = mock_path_instance
            mock_path_instance.exists.return_value = False

            with pytest.raises(FileNotFoundError):
                service._load_template("nonexistent.html")
