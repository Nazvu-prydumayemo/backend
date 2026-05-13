from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import LoggingMiddleware

# Initialize logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    loki_url=settings.LOKI_URL,
    loki_user=settings.LOKI_USER,
    loki_password=settings.LOKI_PASSWORD,
)

app = FastAPI(
    title="NP-API", openapi_url=("/openapi.json" if settings.environment == "dev" else None)
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

app.include_router(api_router, prefix="/api/v1")
