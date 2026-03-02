from datetime import UTC, datetime

from fastapi import APIRouter

from .schemas import StatusResponse

router = APIRouter(prefix="/status", tags=["Status"])


@router.get(
    "/",
    response_model=StatusResponse,
    summary="Full Health Check",
    description="Returns detailed system status and current server time.",
)
async def status() -> StatusResponse:
    return StatusResponse(
        status="ok",
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/ping",
    response_model=str,
    summary="Health Check",
    description="Returns a 'pong' string to verify the server is alive and reachable.",
)
async def ping() -> str:
    return "pong"
