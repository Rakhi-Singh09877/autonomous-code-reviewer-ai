from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel

from app.core.logging import logger, request_id_ctx_var
from app.domain.exceptions.agent_exceptions import (
    AgentException,
    LLMException,
    LLMConnectionException,
    LLMRateLimitException,
    LLMInvalidAPIKeyException,
)
from app.domain.exceptions.repository_exceptions import (
    RepositoryLoaderException,
    InvalidRepositoryURLException,
    SecurityException,
    ZipSlipException,
    CloneTimeoutException,
)

class ErrorResponse(BaseModel):
    """
    Standardized API Error Response Schema.
    """
    error_code: str
    message: str
    detail: str  # Added for FastAPI/Starlette client backward compatibility
    request_id: str
    timestamp: str

def create_error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    """
    Creates a standardized JSONResponse error body.
    """
    content = {
        "error_code": error_code,
        "message": message,
        "detail": message,  # Standard fallback detail key
        "request_id": request_id_ctx_var.get() or "",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return JSONResponse(status_code=status_code, content=content)

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers custom exception mapping filters to the FastAPI instance.
    """
    # 1. Pydantic request validation exceptions
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "")
            errors.append(f"{loc}: {msg}")
        message = "Request validation failed: " + "; ".join(errors)
        logger.error(f"Validation error for {request.method} {request.url.path}: {message}")
        return create_error_response(422, "VALIDATION_ERROR", message)

    # 2. Standard Starlette HTTP exceptions
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP exception occurred at {request.method} {request.url.path}: {exc.detail}")
        return create_error_response(exc.status_code, "HTTP_ERROR", exc.detail)

    # 3. Domain exception mappings
    @app.exception_handler(InvalidRepositoryURLException)
    async def invalid_repo_url_handler(request: Request, exc: InvalidRepositoryURLException):
        logger.error(f"Invalid Repository URL Exception: {exc}")
        return create_error_response(400, "INVALID_REPOSITORY_URL", str(exc))

    @app.exception_handler(ZipSlipException)
    async def zip_slip_handler(request: Request, exc: ZipSlipException):
        logger.error(f"Zip Slip Exception: {exc}")
        return create_error_response(400, "ZIP_SLIP_VIOLATION", str(exc))

    @app.exception_handler(SecurityException)
    async def security_handler(request: Request, exc: SecurityException):
        logger.error(f"Security Exception: {exc}")
        return create_error_response(400, "SECURITY_VIOLATION", str(exc))

    @app.exception_handler(CloneTimeoutException)
    async def clone_timeout_handler(request: Request, exc: CloneTimeoutException):
        logger.error(f"Clone Timeout Exception: {exc}")
        return create_error_response(504, "REPOSITORY_CLONE_TIMEOUT", str(exc))

    @app.exception_handler(RepositoryLoaderException)
    async def repo_loader_handler(request: Request, exc: RepositoryLoaderException):
        logger.error(f"Repository Loader Exception: {exc}")
        return create_error_response(500, "REPOSITORY_LOADER_ERROR", str(exc))

    @app.exception_handler(LLMInvalidAPIKeyException)
    async def llm_api_key_handler(request: Request, exc: LLMInvalidAPIKeyException):
        logger.error(f"LLM Invalid API Key Exception: {exc}")
        return create_error_response(502, "LLM_INVALID_API_KEY", str(exc))

    @app.exception_handler(LLMRateLimitException)
    async def llm_rate_limit_handler(request: Request, exc: LLMRateLimitException):
        logger.error(f"LLM Rate Limit Exception: {exc}")
        return create_error_response(429, "LLM_RATE_LIMIT_EXCEEDED", str(exc))

    @app.exception_handler(LLMConnectionException)
    async def llm_connection_handler(request: Request, exc: LLMConnectionException):
        logger.error(f"LLM Connection Exception: {exc}")
        return create_error_response(502, "LLM_CONNECTION_FAILED", str(exc))

    @app.exception_handler(LLMException)
    async def llm_exception_handler(request: Request, exc: LLMException):
        logger.error(f"LLM Exception: {exc}")
        return create_error_response(500, "LLM_SERVICE_ERROR", str(exc))

    @app.exception_handler(AgentException)
    async def agent_exception_handler(request: Request, exc: AgentException):
        logger.error(f"Agent Exception: {exc}")
        return create_error_response(500, "AGENT_ERROR", str(exc))

    # 4. Catch-all unhandled system exceptions
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Log complete traceback details internally using logger.exception
        logger.exception(f"Unhandled system exception occurred during request {request.method} {request.url.path}: {exc}")
        return create_error_response(
            500,
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred. Please contact the administrator."
        )
