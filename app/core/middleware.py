"""HTTP logging middleware for FastAPI."""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    Captures method, path, status code, response time, and client IP.
    """

    def _get_client_ip(self, request: Request) -> str:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            forwarded_ips = [ip.strip() for ip in x_forwarded_for.split(",")]
            for ip in forwarded_ips:
                if ip:
                    return ip

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip:
            return x_real_ip.strip()

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Get client info
        client_ip = self._get_client_ip(request)

        # Log request
        logger.info(
            "Request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "query_params": dict(request.query_params),
            },
        )

        try:
            # Call the next middleware/endpoint
            response = await call_next(request)

            # Calculate response time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                "Response",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "response_time_ms": process_time * 1000,
                    "client_ip": client_ip,
                },
            )

            # Add response time header
            response.headers["X-Process-Time"] = str(process_time)
            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                "Exception",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "response_time_ms": process_time * 1000,
                    "client_ip": client_ip,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
