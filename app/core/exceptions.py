from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


import math


class AppError(Exception):
    """Base application error. Carries its own HTTP status and message."""
    status_code = 500
    message = "Internal server error"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)

    @property
    def headers(self) -> dict[str, str] | None:
        """Extra HTTP headers for the error response, if any."""
        return None


class PayloadTooLargeError(AppError):
    """The input JSON exceeds the allowed limit."""
    status_code = 413
    message = "Payload too large"


class AIResponseError(AppError):
    """The AI failed or returned a response that doesn't match the expected format."""
    status_code = 502
    message = "AI response error"


class RateLimitError(AppError):
    """Too many requests to a rate-limited endpoint (/explain)."""
    status_code = 429
    message = "Too many requests"

    def __init__(self, message: str | None = None, retry_after: float = 1):
        super().__init__(message)
        # Whole seconds, rounded up and never 0: retrying earlier is pointless.
        self.retry_after = max(1, math.ceil(retry_after))

    @property
    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)}


def register_error_handlers(app: FastAPI):
    """Register global error handlers on the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": "Invalid request",
                "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
                "details": exc.errors(),
                "path": request.url.path
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": str(exc) if app.debug else "An unexpected error occurred. Please try again later.",
                "path": request.url.path
            }
        )