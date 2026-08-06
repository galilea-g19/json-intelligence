from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        max_size = settings.max_body_bytes

        def too_large() -> JSONResponse:
            # Return the response directly: an exception raised inside a
            # BaseHTTPMiddleware does NOT go through the global exception handlers.
            return JSONResponse(
                status_code=413,
                content={
                    "error": f"Request body too large. Max {max_size} bytes allowed.",
                    "status_code": 413,
                    "path": request.url.path,
                },
            )

        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > max_size:
            return too_large()

        # If there's no reliable content-length, read the body and check it
        body = await request.body()
        if len(body) > max_size:
            return too_large()

        # Re-build the request so that the endpoints can read it again
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive

        return await call_next(request)
