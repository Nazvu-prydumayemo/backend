"""Notification helpers for sending booking emails."""

import logging
from datetime import date
from decimal import Decimal

from fastapi_mail import NameEmail

from app.features.email.service import email_service

logger = logging.getLogger(__name__)


async def send_booking_confirmation(
    recipient_email: str,
    user_name: str,
    court_name: str,
    booking_date: date,
    time_slots: str,
    total_price: Decimal,
) -> bool:
    """Send a booking confirmation email."""
    try:
        return await email_service.send_booking_confirmation(
            recipient_email=NameEmail(email=recipient_email, name=user_name),
            user_name=user_name,
            court_name=court_name,
            booking_date=booking_date.isoformat(),
            time_slots=time_slots,
            total_price=str(total_price),
        )
    except Exception as e:
        logger.error("Failed to send booking confirmation email: %s", e)
        return False
