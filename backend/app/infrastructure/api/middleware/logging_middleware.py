import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger, request_id_ctx_var

class RequestTimingAndLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting trace timings in headers and logging structured request summary details.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Response-Time-Ms"] = f"{process_time_ms:.2f}"
        
        request_id = request_id_ctx_var.get() or ""
        method = request.method
        route = request.url.path
        status_code = response.status_code
        
        # Ensure failed requests are logged with error priority level containing timing details
        if status_code >= 400:
            logger.error(
                "Request failed: request_id=%s route=%s method=%s execution_time=%.2fms status_code=%d",
                request_id, route, method, process_time_ms, status_code
            )
        else:
            logger.info(
                "Request completed: request_id=%s route=%s method=%s execution_time=%.2fms status_code=%d",
                request_id, route, method, process_time_ms, status_code
            )
            
        return response
