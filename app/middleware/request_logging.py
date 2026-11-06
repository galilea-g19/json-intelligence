import time
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status and duration of every request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            # An unhandled error propagates through this middleware before the
            # global handler turns it into a 500, so without this branch the
            # request would never reach the log (MW-07). It is re-raised so the
            # handler in app.core.exceptions still builds the response.
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                f"{request.method} {request.url.path} -> 500 "
                f"({elapsed_ms:.0f} ms) [{type(exc).__name__}]"
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} "
            f"({elapsed_ms:.0f} ms)"
        )
        return response
