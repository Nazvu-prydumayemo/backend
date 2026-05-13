import asyncio
import json
import logging
import sys
import time
from typing import Any

import aiohttp

# Standard LogRecord attributes that should not be included as extra fields
STANDARD_LOG_ATTRS = {
    "name",
    "msg",
    "args",
    "created",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "thread",
    "threadName",
    "exc_info",
    "exc_text",
    "stack_info",
    "taskName",
    "asctime",
    "getMessage",
}


class StructuredFormatter(logging.Formatter):
    """
    Formats log records as JSON with structured metadata.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "message": record.getMessage(),
        }

        # Add any extra fields from logger.info(..., extra={...})
        # These are added directly to the LogRecord's __dict__
        for key, value in record.__dict__.items():
            # Skip standard LogRecord attributes, private attributes, and callables
            if key not in STANDARD_LOG_ATTRS and not key.startswith("_") and not callable(value):
                try:
                    # Try to JSON-serialize the value to ensure it's safe
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    # Skip values that can't be JSON-serialized
                    pass

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class LokiHandler(logging.Handler):
    """
    Async handler to ship logs to Loki.
    Uses a queue to avoid blocking the main thread.
    """

    def __init__(
        self,
        loki_url: str,
        job_name: str = "np-backend",
        loki_user: str | None = None,
        loki_password: str | None = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
    ):
        super().__init__()
        self.loki_url = loki_url.rstrip("/")
        self.job_name = job_name
        self.loki_user = loki_user
        self.loki_password = loki_password
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: asyncio.Queue[Any] | None = None
        self.session: aiohttp.ClientSession | None = None
        self.task: asyncio.Task | None = None
        self._initialized = False

    def initialize_async(self) -> None:
        """Initialize async components. Must be called with a running event loop (e.g., from FastAPI lifespan)."""
        if self._initialized:
            return

        loop = asyncio.get_running_loop()  # Raises RuntimeError if called outside a running loop

        self.queue = asyncio.Queue()
        self.session = aiohttp.ClientSession()

        # Start the background task that processes logs
        self.task = loop.create_task(self._process_logs())
        self._initialized = True

    def emit(self, record: logging.LogRecord) -> None:
        """Add log record to queue for async processing."""
        if not self._initialized:
            # Handler not yet initialized from lifespan; skip Loki push for this record
            return

        try:
            msg = self.format(record)
            if self.queue:
                self.queue.put_nowait(msg)
        except Exception:
            self.handleError(record)

    async def _process_logs(self) -> None:
        """Process logs from queue and send to Loki."""
        batch = []

        while True:
            try:
                # Wait for either a message or timeout
                try:
                    assert self.queue is not None
                    msg = await asyncio.wait_for(self.queue.get(), timeout=self.flush_interval)
                    batch.append(msg)
                except TimeoutError:
                    # Timeout is expected; triggers a periodic flush of partial batches
                    pass

                # Send batch if full or timed out with messages
                if len(batch) >= self.batch_size or (
                    batch and self.task  # Timeout occurred
                ):
                    await self._send_batch(batch)
                    batch = []
            except Exception as e:
                print(f"Error processing logs: {e}", file=sys.stderr)

    async def _send_batch(self, batch: list[str]) -> None:
        """Send a batch of logs to Loki."""
        if not batch or not self.session:
            return

        try:
            # Use wall-clock time in nanoseconds for Loki
            timestamp = str(time.time_ns())
            streams = [
                {
                    "stream": {"job": self.job_name},
                    "values": [[timestamp, log] for log in batch],
                }
            ]

            payload = {"streams": streams}

            headers = {"Content-Type": "application/json"}
            auth = None
            if self.loki_user and self.loki_password:
                auth = aiohttp.BasicAuth(self.loki_user, self.loki_password)

            async with self.session.post(
                f"{self.loki_url}/loki/api/v1/push",
                json=payload,
                headers=headers,
                auth=auth,
            ) as response:
                if response.status != 204:
                    error_text = await response.text()
                    print(
                        f"Loki error: {response.status} - {error_text}",
                        file=sys.stderr,
                    )
        except Exception as e:
            print(f"Error sending logs to Loki: {e}", file=sys.stderr)

    async def _close_async(self) -> None:
        """Clean up resources asynchronously."""
        if self.task:
            self.task.cancel()
        if self.session:
            await self.session.close()

    def close(self) -> None:
        """Clean up resources (sync wrapper for logging.Handler interface)."""
        super().close()
        if not self._initialized:
            return
        try:
            loop = asyncio.get_running_loop()
            # Fire-and-forget async cleanup; the task runs on the active loop.
            # Errors from _close_async are non-critical (session/task teardown).
            loop.create_task(self._close_async())
        except RuntimeError:
            # No running event loop; cancel the background task directly
            if self.task and not self.task.done():
                self.task.cancel()


def setup_logging(
    log_level: str = "INFO",
    loki_url: str | None = None,
    loki_user: str | None = None,
    loki_password: str | None = None,
    job_name: str = "np-backend",
) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        loki_url: URL to Loki instance
        loki_user: Username for Loki authentication
        loki_password: Password for Loki authentication
        job_name: Job name for logs in Loki
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    json_formatter = StructuredFormatter()
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Add Loki handler if URL is provided
    if loki_url:
        loki_handler = LokiHandler(
            loki_url=loki_url,
            job_name=job_name,
            loki_user=loki_user,
            loki_password=loki_password,
        )
        loki_handler.setFormatter(json_formatter)
        loki_handler.setLevel(log_level)
        root_logger.addHandler(loki_handler)

    # Set library loggers to WARNING to reduce noise
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
