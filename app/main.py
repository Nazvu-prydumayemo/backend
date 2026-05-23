"""Application entry point. Configures FastAPI app, lifespan events, and logging."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.core.logging_config import LokiHandler, setup_logging
from app.core.middleware import LoggingMiddleware
from app.features.notifications.scheduler import reschedule_pending_reminders, scheduler

# Initialize logging (console handler is active immediately; Loki handler is started in lifespan)
setup_logging(
    log_level=settings.LOG_LEVEL,
    loki_url=settings.LOKI_URL,
    loki_user=settings.LOKI_USER,
    loki_password=settings.LOKI_PASSWORD,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async context manager for application lifespan events.

    Initializes Loki logging, starts the APScheduler, and recovers pending
    reminder jobs on startup. Shuts down the scheduler and Loki handlers on
    shutdown.
    """
    # Initialize async components of any LokiHandlers now that the event loop is running
    root_logger = logging.getLogger()
    loki_handlers = [h for h in root_logger.handlers if isinstance(h, LokiHandler)]
    for handler in loki_handlers:
        await handler._ensure_initialized()

    # Start APScheduler and recover pending reminders
    scheduler.start()
    await reschedule_pending_reminders()

    yield

    # Shutdown scheduler
    scheduler.shutdown(wait=False)

    # Clean up LokiHandlers on shutdown
    for handler in loki_handlers:
        await handler._close_async()


app = FastAPI(
    title="NP-API",
    openapi_url=("/openapi.json" if settings.environment == "dev" else None),
    lifespan=lifespan,
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.include_router(api_router, prefix="/api/v1")
