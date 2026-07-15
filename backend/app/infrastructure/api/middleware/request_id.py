import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import request_id_ctx_var

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware extracting or generating unique X-Request-ID headers and mapping them to context variables.
    """
    async def dispatch(self, request: Request, call_next):
        # Retrieve incoming header or generate a fresh trace token
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Set the request ID in thread-local/coroutine-local context
        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clean up context tracking references
            request_id_ctx_var.reset(token)
