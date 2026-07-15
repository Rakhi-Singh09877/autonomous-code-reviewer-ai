import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger, request_id_ctx_var
from app.infrastructure.registry import services_registry

class RequestTimingAndLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting trace timings in headers, logging request details, and recording operational metrics.
    """
    async def dispatch(self, request: Request, call_next):
        metrics = services_registry.metrics
        
        # Increment active requests gauge count
        metrics.record_request_started()
        
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            
            latency_seconds = time.perf_counter() - start_time
            process_time_ms = latency_seconds * 1000.0
            response.headers["X-Response-Time-Ms"] = f"{process_time_ms:.2f}"
            
            request_id = request_id_ctx_var.get() or ""
            method = request.method
            route = request.url.path
            status_code = response.status_code
            
            # Record completed request metrics (handles gauge decrement internally)
            metrics.record_request_completed(method, route, status_code, latency_seconds)
            
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
            
        except Exception:
            # Decrement active requests gauge even if route raises an unhandled exception
            metrics.record_request_completed(
                request.method,
                request.url.path,
                500,
                time.perf_counter() - start_time
            )
            raise
