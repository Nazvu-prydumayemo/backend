"""Logging configuration with structured JSON output and Loki shipping."""

import asyncio
import json
import logging
import sys
import threading
import time
from collections import deque
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
        """Format a log record as a JSON string with structured metadata."""
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

        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_ATTRS and not key.startswith("_") and not callable(value):
                try:
                    json.dumps(value)
                except (TypeError, ValueError):
                    continue

                log_data[key] = value

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
        """Initialize the Loki logging handler.

        Args:
            loki_url: URL of the Loki instance.
            job_name: Job label for logs in Loki.
            loki_user: Optional username for Loki authentication.
            loki_password: Optional password for Loki authentication.
            batch_size: Maximum number of log entries per batch.
            flush_interval: Maximum seconds to wait before flushing a batch.
        """
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
        self._init_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._init_check_lock = threading.Lock()
        self.dropped_logs = 0
        self._drop_lock = threading.Lock()
        self._shutdown = asyncio.Event()
        self._startup_buffer: deque[str] = deque(maxlen=1000)
        self._startup_buffer_lock = threading.Lock()

    async def _ensure_initialized(self):
        """Idempotent async initialization."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            if self._shutdown.is_set():
                return

            self.queue = asyncio.Queue(maxsize=10_000)
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10), connector=aiohttp.TCPConnector(limit=20)
            )

            with self._startup_buffer_lock:
                for msg in self._startup_buffer:
                    try:
                        await self.queue.put(msg)
                    except asyncio.QueueFull:
                        with self._drop_lock:
                            self.dropped_logs += 1
                self._startup_buffer.clear()

            self.task = asyncio.create_task(self._process_logs())
            self._initialized = True

    def emit(self, record: logging.LogRecord) -> None:
        """Add log record to queue for async processing."""
        if self._shutdown.is_set():
            with self._drop_lock:
                self.dropped_logs += 1
            return

        if not self._initialized and self._init_task is None:
            with self._init_check_lock:
                if not self._initialized and self._init_task is None:
                    try:
                        loop = asyncio.get_running_loop()
                        self._init_task = loop.create_task(self._ensure_initialized())
                    except RuntimeError:
                        with self._drop_lock:
                            self.dropped_logs += 1
                        return

        try:
            msg = self.format(record)
        except Exception:
            self.handleError(record)
            return

        if self.queue is None:
            with self._startup_buffer_lock:
                if len(self._startup_buffer) == self._startup_buffer.maxlen:
                    with self._drop_lock:
                        self.dropped_logs += 1

                self._startup_buffer.append(msg)
            return

        try:
            self.queue.put_nowait(msg)
        except asyncio.QueueFull:
            with self._drop_lock:
                self.dropped_logs += 1
        except (AttributeError, RuntimeError):
            with self._drop_lock:
                self.dropped_logs += 1
        except Exception:
            self.handleError(record)

    async def _process_logs(self) -> None:
        """Process logs from queue and send to Loki."""
        batch: list[str] = []
        last_flush = time.monotonic()

        while True:
            queue = self.queue

            if self._shutdown.is_set() and (queue is None or queue.empty()):
                break

            try:
                if queue is None:
                    await asyncio.sleep(self.flush_interval)
                    continue

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=self.flush_interval)
                    batch.append(msg)

                except TimeoutError:
                    # No log item arrived within flush_interval; continue processing loop.
                    continue

                now = time.monotonic()

                if batch and (
                    len(batch) >= self.batch_size or (now - last_flush >= self.flush_interval)
                ):
                    await self._send_batch(batch)
                    batch.clear()
                    last_flush = now

            except Exception as e:
                print(f"Error processing logs: {e}", file=sys.stderr)

        queue = self.queue

        if queue is not None:
            while not queue.empty():
                try:
                    msg = queue.get_nowait()
                    batch.append(msg)

                    if len(batch) >= self.batch_size:
                        await self._send_batch(batch)
                        batch.clear()

                except asyncio.QueueEmpty:
                    break
                except Exception:
                    break

        if batch:
            try:
                await self._send_batch(batch)
            except Exception as e:
                print(f"Error flushing final batch: {e}", file=sys.stderr)

    async def _send_batch(self, batch: list[str]) -> None:
        """Send a batch of logs to Loki."""
        if not batch or not self.session:
            return

        try:
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
                        f"Loki error:{response.status} - {error_text}",
                        file=sys.stderr,
                    )
        except TimeoutError:
            print(f"Loki timeout: unable to send {len(batch)} logs", file=sys.stderr)
        except aiohttp.ClientError as e:
            print(f"Loki network error: {type(e).__name__}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Loki error: {type(e).__name__}: {e}", file=sys.stderr)

    async def _close_async(self) -> None:
        """Clean up resources asynchronously."""

        self._shutdown.set()

        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
            try:
                await self._init_task
            except asyncio.CancelledError:
                pass

        if self.task:
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        if self.session:
            await self.session.close()

    def close(self) -> None:
        """Clean up resources (sync wrapper for logging.Handler interface)."""
        try:
            try:
                asyncio.get_running_loop()
                self._cleanup_task = asyncio.ensure_future(self._close_async())
                return
            except RuntimeError:
                pass

            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    return
                if loop.is_running():
                    self._cleanup_task = asyncio.ensure_future(self._close_async())
                else:
                    loop.run_until_complete(self._close_async())
            except Exception as e:
                print(f"Loki handler loop cleanup error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Loki handler close error: {e}", file=sys.stderr)
        finally:
            super().close()


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
