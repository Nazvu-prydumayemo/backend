from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings

app = FastAPI(
    title="NP-API", openapi_url=("/openapi.json" if settings.environment == "dev" else None)
)

app.include_router(api_router, prefix="/api/v1")
