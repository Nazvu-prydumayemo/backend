from fastapi import APIRouter

from app.features.ping.router import router as ping_router

api_router = APIRouter()
api_router.include_router(ping_router)
