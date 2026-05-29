from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large. Max 1 MB allowed.")
        
        # Si no hay content-length, leemos el body y verificamos
        body = await request.body()
        if len(body) > MAX_BODY_SIZE:
            raise HTTPException(status_code=413, detail="Request body too large. Max 1 MB allowed.")
        
        # Re-build the request so that the endpoints can read it again
        async def receive():
            return {"type": "http.request", "body": body}
        request._receive = receive
        
        response = await call_next(request)
        return response