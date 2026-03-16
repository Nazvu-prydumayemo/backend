from fastapi import APIRouter

from app.features.auth.router import router as auth_router
from app.features.ping.router import router as ping_router
from app.features.user.router import account_router, users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(ping_router)
api_router.include_router(users_router)
api_router.include_router(account_router)
