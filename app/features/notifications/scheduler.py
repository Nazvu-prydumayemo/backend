import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from fastapi_mail import NameEmail
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.features.court.models import Court
from app.features.email.service import email_service
from app.features.order.models import Order
from app.features.order.service import format_slot_ranges
from app.features.user.models import User

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def schedule_reminder(order_id: int, first_slot_datetime: datetime) -> None:
    """Schedule a reminder job to fire 1 hour before the booking."""
    reminder_time = first_slot_datetime - timedelta(hours=1)
    now = datetime.now(UTC)

    if reminder_time <= now:
        logger.info("Order %d: reminder time already passed, sending with 10s delay", order_id)
        reminder_time = now + timedelta(seconds=10)

    scheduler.add_job(
        send_booking_reminder,
        trigger="date",
        run_date=reminder_time,
        args=[order_id],
        id=f"booking_reminder_{order_id}",
        replace_existing=True,
    )
    logger.info("Order %d: reminder scheduled for %s", order_id, reminder_time.isoformat())


def cancel_reminder(order_id: int) -> None:
    """Cancel a scheduled reminder job for an order."""
    try:
        scheduler.remove_job(f"booking_reminder_{order_id}")
        logger.info("Order %d: reminder cancelled", order_id)
    except Exception:
        pass


async def send_booking_reminder(order_id: int) -> None:
    """APScheduler job: send reminder email and mark order as notified."""
    async with AsyncSessionLocal() as db:
        query = select(Order).where(Order.id == order_id).options(selectinload(Order.booking_slots))
        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order or order.reminder_sent:
            logger.info("Order %d: already notified or not found, skipping", order_id)
            return

        court_query = select(Court).where(Court.id == order.court_id)
        court_result = await db.execute(court_query)
        court = court_result.scalar_one_or_none()

        if not court:
            logger.warning("Order %d: court %d not found", order_id, order.court_id)
            order.reminder_sent = True
            await db.commit()
            return

        user_query = select(User).where(User.id == order.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            logger.warning("Order %d: user %d not found", order_id, order.user_id)
            order.reminder_sent = True
            await db.commit()
            return

        if not order.booking_slots:
            logger.warning("Order %d: no booking slots, marking as notified", order_id)
            order.reminder_sent = True
            await db.commit()
            return

        location = court.location or "Check your booking details"
        time_slots = format_slot_ranges(order.booking_slots)

        success = await email_service.send_booking_reminder(
            NameEmail(email=user.email, name=user.firstname),
            user.firstname,
            court.name,
            order.booking_date.isoformat() if order.booking_date else "",
            time_slots,
            location,
        )

        order.reminder_sent = True
        await db.commit()

        if success:
            logger.info("Order %d: reminder email sent successfully", order_id)
        else:
            logger.warning("Order %d: reminder email failed to send", order_id)


async def reschedule_pending_reminders() -> None:
    """On startup, re-schedule reminder jobs for orders that haven't been notified yet."""
    async with AsyncSessionLocal() as db:
        query = (
            select(Order)
            .where(Order.reminder_sent.is_(False))
            .options(selectinload(Order.booking_slots))
        )
        result = await db.execute(query)
        orders = result.scalars().all()

        count = 0
        for order in orders:
            if not order.booking_slots:
                continue
            first_slot = min(order.booking_slots, key=lambda s: (s.slot_date, s.start_time))
            slot_datetime = datetime.combine(
                first_slot.slot_date, first_slot.start_time, tzinfo=UTC
            )
            schedule_reminder(order.id, slot_datetime)
            count += 1

        logger.info("Recovered %d pending reminders", count)
