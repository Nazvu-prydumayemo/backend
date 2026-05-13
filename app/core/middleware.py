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

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Get client info
        client_ip = request.client.host if request.client else "unknown"

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
