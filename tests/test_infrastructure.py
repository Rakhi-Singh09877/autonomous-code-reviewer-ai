import io
import json
import logging
import uuid
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

# Ensure app directory is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import Settings, settings
from app.core.logging import JsonFormatter, PlainFormatter, request_id_ctx_var, setup_logging
from app.infrastructure.api.middleware.request_id import RequestIDMiddleware
from app.infrastructure.api.middleware.security import SecurityHeadersMiddleware
from app.infrastructure.api.middleware.logging_middleware import RequestTimingAndLoggingMiddleware
from app.infrastructure.api.errors import register_exception_handlers, ErrorResponse
from app.infrastructure.database.repository import SQLAlchemyDBAdapter
from app.domain.exceptions.agent_exceptions import LLMRateLimitException
from app.domain.exceptions.repository_exceptions import InvalidRepositoryURLException
from app.infrastructure.api.dependencies import get_db_port, get_llm_port, get_rag_port, get_loader_port
from app.main import lifespan

def test_json_formatter_formatting():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message format",
        args=None,
        exc_info=None
    )
    token = request_id_ctx_var.set("trace-token-123")
    try:
        formatter = JsonFormatter()
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message format"
        assert log_data["request_id"] == "trace-token-123"
    finally:
        request_id_ctx_var.reset(token)

def test_plain_formatter_formatting():
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=15,
        msg="Plain text warning",
        args=None,
        exc_info=None
    )
    token = request_id_ctx_var.set("trace-token-456")
    try:
        formatter = PlainFormatter()
        result = formatter.format(record)
        assert "[WARNING]" in result
        assert "[trace-token-456]" in result
        assert "Plain text warning" in result
    finally:
        request_id_ctx_var.reset(token)

def test_request_id_middleware_propagation():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    async def get_test():
        return {"current_request_id": request_id_ctx_var.get()}
        
    client = TestClient(app)
    
    res = client.get("/test")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    generated_id = res.headers["X-Request-ID"]
    assert res.json()["current_request_id"] == generated_id
    
    client_id = str(uuid.uuid4())
    res = client.get("/test", headers={"X-Request-ID": client_id})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == client_id
    assert res.json()["current_request_id"] == client_id

def test_provider_driven_config_validation():
    cfg = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="",
        EMBEDDING_PROVIDER="local"
    )
    with pytest.raises(ValueError) as exc:
        cfg.validate_config(force=True)
    assert "ANTHROPIC_API_KEY is required" in str(exc.value)

    cfg = Settings(
        LLM_PROVIDER="local",
        EMBEDDING_PROVIDER="openai",
        OPENAI_API_KEY=""
    )
    with pytest.raises(ValueError) as exc:
        cfg.validate_config(force=True)
    assert "OPENAI_API_KEY is required" in str(exc.value)

    cfg = Settings(
        LLM_PROVIDER="local",
        EMBEDDING_PROVIDER="local",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY=""
    )
    cfg.validate_config(force=True)

@pytest.mark.asyncio
async def test_database_port_initialize():
    db = SQLAlchemyDBAdapter(database_url="sqlite:///:memory:")
    await db.initialize()
    assert await db.check_health() is True

@pytest.mark.asyncio
async def test_lifespan_startup_failures_raise_runtime_error():
    app = FastAPI()
    mock_db = MagicMock()
    mock_db.initialize = AsyncMock()
    mock_db.check_health = AsyncMock(return_value=False)
    
    mock_llm = MagicMock()
    mock_llm.check_health = AsyncMock(return_value=True)
    
    mock_rag = MagicMock()
    mock_rag.check_health = AsyncMock(return_value=True)
    
    modules_copy = sys.modules.copy()
    if "pytest" in modules_copy:
        del modules_copy["pytest"]
    
    with patch("sys.modules", modules_copy), \
         patch("app.main.get_db_port", return_value=mock_db), \
         patch("app.main.get_llm_port", return_value=mock_llm), \
         patch("app.main.get_rag_port", return_value=mock_rag), \
         patch("app.main.setup_logging"), \
         patch("app.core.config.Settings.validate_config"):
         
         with pytest.raises(RuntimeError) as exc:
             async with lifespan(app):
                 pass
         assert "Database health check failed" in str(exc.value)

# ==========================================
# New Infrastructure Phase 2 Part 2 Tests
# ==========================================

def test_security_headers_middleware():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    
    @app.get("/ping")
    async def ping():
        return {"ping": "pong"}
        
    client = TestClient(app)
    res = client.get("/ping")
    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "no-referrer-when-downgrade"
    assert "geolocation" in res.headers["Permissions-Policy"]

def test_request_timing_and_logging_middleware(caplog):
    app = FastAPI()
    app.add_middleware(RequestTimingAndLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware) # Inner middleware to inject request_id
    
    @app.get("/ping")
    async def ping():
        return {"ping": "pong"}
        
    @app.get("/fail-route")
    async def fail_route():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Some Bad Request")
        
    client = TestClient(app)
    
    # 1. Success request
    with caplog.at_level(logging.INFO):
        res = client.get("/ping")
        assert res.status_code == 200
        assert "X-Response-Time-Ms" in res.headers
        assert float(res.headers["X-Response-Time-Ms"]) >= 0
        
        success_logs = [r.message for r in caplog.records if "Request completed" in r.message]
        assert len(success_logs) == 1
        assert "route=/ping" in success_logs[0]
        assert "method=GET" in success_logs[0]
        assert "status_code=200" in success_logs[0]
        
    # 2. Failed request
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        res = client.get("/fail-route")
        assert res.status_code == 400
        
        fail_logs = [r.message for r in caplog.records if "Request failed" in r.message]
        assert len(fail_logs) == 1
        assert "route=/fail-route" in fail_logs[0]
        assert "status_code=400" in fail_logs[0]

def test_cors_middleware():
    from fastapi.middleware.cors import CORSMiddleware
    app = FastAPI()
    # Mock settings.CORS_ALLOWED_ORIGINS during middleware initialization
    allowed_origins = ["http://localhost:3000", "https://example.com"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/ping")
    async def ping():
        return {"ping": "pong"}
        
    client = TestClient(app)
    
    # Valid origin
    res = client.get("/ping", headers={"Origin": "http://localhost:3000"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    
    # Invalid origin
    res = client.get("/ping", headers={"Origin": "https://malicious.com"})
    assert "access-control-allow-origin" not in res.headers

def test_exception_handler_domain_mappings():
    app = FastAPI()
    register_exception_handlers(app)
    
    @app.get("/domain-error")
    async def trigger_domain_error():
        raise InvalidRepositoryURLException("Provided repo URL format is invalid")
        
    @app.get("/rate-limit")
    async def trigger_rate_limit():
        raise LLMRateLimitException("Anthropic API rate limit exceeded")
        
    @app.get("/generic-error")
    async def trigger_generic_error():
        raise RuntimeError("Severe raw internal error")
        
    client = TestClient(app, raise_server_exceptions=False)
    
    # 1. InvalidRepositoryURLException -> 400
    res = client.get("/domain-error")
    assert res.status_code == 400
    data = res.json()
    assert data["error_code"] == "INVALID_REPOSITORY_URL"
    assert "Provided repo URL format is invalid" in data["message"]
    assert "request_id" in data
    assert "timestamp" in data
    
    # 2. LLMRateLimitException -> 429
    res = client.get("/rate-limit")
    assert res.status_code == 429
    data = res.json()
    assert data["error_code"] == "LLM_RATE_LIMIT_EXCEEDED"
    
    # 3. Unhandled Exception -> 500 without traceback details
    res = client.get("/generic-error")
    assert res.status_code == 500
    data = res.json()
    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "An unexpected error occurred" in data["message"]
    assert "Severe raw internal error" not in data["message"] # Hides raw exception details

def test_custom_validation_error_response():
    app = FastAPI()
    register_exception_handlers(app)
    
    from pydantic import BaseModel
    class Item(BaseModel):
        name: str
        price: float
        
    @app.post("/items")
    async def create_item(item: Item):
        return item
        
    client = TestClient(app)
    # Trigger validation error by passing invalid price (string instead of float)
    res = client.post("/items", json={"name": "Widget", "price": "not-a-float"})
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "Request validation failed" in data["message"]
    assert "body.price" in data["message"]

# ==========================================
# Phase 3 Observability Tests
# ==========================================

def test_liveness_probe():
    from app.main import app
    client = TestClient(app)
    res = client.get("/api/v1/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}

def test_readiness_probe_success():
    from app.main import app
    
    mock_db = MagicMock()
    mock_db.check_health = AsyncMock(return_value=True)
    mock_llm = MagicMock()
    mock_llm.check_health = AsyncMock(return_value=True)
    mock_rag = MagicMock()
    mock_rag.check_health = AsyncMock(return_value=True)
    mock_loader = MagicMock()
    mock_loader.check_health = MagicMock(return_value=True)

    app.dependency_overrides[get_db_port] = lambda: mock_db
    app.dependency_overrides[get_llm_port] = lambda: mock_llm
    app.dependency_overrides[get_rag_port] = lambda: mock_rag
    app.dependency_overrides[get_loader_port] = lambda: mock_loader
    
    try:
        client = TestClient(app)
        res = client.get("/api/v1/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["details"]["database"] == "healthy"
    finally:
        app.dependency_overrides.clear()

def test_readiness_probe_failure_logging(caplog):
    from app.main import app
    
    mock_db = MagicMock()
    mock_db.check_health = AsyncMock(return_value=True)
    mock_llm = MagicMock()
    mock_llm.check_health = AsyncMock(return_value=True)
    mock_rag = MagicMock()
    mock_rag.check_health = AsyncMock(return_value=False)
    mock_loader = MagicMock()
    mock_loader.check_health = MagicMock(return_value=True)

    app.dependency_overrides[get_db_port] = lambda: mock_db
    app.dependency_overrides[get_llm_port] = lambda: mock_llm
    app.dependency_overrides[get_rag_port] = lambda: mock_rag
    app.dependency_overrides[get_loader_port] = lambda: mock_loader
    
    try:
        with caplog.at_level(logging.ERROR):
            client = TestClient(app)
            res = client.get("/api/v1/ready")
            assert res.status_code == 503
            data = res.json()
            assert data["status"] == "not_ready"
            assert data["details"]["rag"] == "unhealthy"
            
            error_logs = [r.message for r in caplog.records if "Readiness check failed" in r.message]
            assert len(error_logs) == 1
            assert "rag" in error_logs[0]
    finally:
        app.dependency_overrides.clear()

def test_metrics_endpoint_content_type_and_histogram_labeled_export():
    from app.main import app
    client = TestClient(app)
    
    client.get("/api/v1/live")
    
    res = client.get("/api/v1/metrics")
    assert res.status_code == 200
    assert "text/plain; version=0.0.4" in res.headers["content-type"]
    
    content = res.text
    assert "http_requests_total" in content
    assert 'method="GET"' in content
    assert 'path="/api/v1/live"' in content
    assert 'status="200"' in content
    
    assert "http_request_duration_seconds_bucket" in content
    assert "http_request_duration_seconds_sum" in content
    assert "http_request_duration_seconds_count" in content

def test_concurrent_request_accounting():
    from app.infrastructure.registry import services_registry
    metrics = services_registry.metrics
    
    initial_active = metrics._active_requests._value.get()
    
    metrics.record_request_started()
    metrics.record_request_started()
    metrics.record_request_started()
    assert metrics._active_requests._value.get() == initial_active + 3
    
    metrics.record_request_completed("GET", "/concurrent-test", 200, 0.05)
    assert metrics._active_requests._value.get() == initial_active + 2
    
    metrics.record_request_completed("GET", "/concurrent-test", 200, 0.05)
    metrics.record_request_completed("GET", "/concurrent-test", 200, 0.05)
    assert metrics._active_requests._value.get() == initial_active

def test_active_request_gauge_decrement_after_exceptions():
    from app.infrastructure.registry import services_registry
    metrics = services_registry.metrics
    initial_active = metrics._active_requests._value.get()
    
    app = FastAPI()
    app.add_middleware(RequestTimingAndLoggingMiddleware)
    
    @app.get("/error-path")
    async def error_path():
        raise RuntimeError("Testing exceptions decrement")
        
    client = TestClient(app, raise_server_exceptions=False)
    client.get("/error-path")
    
    assert metrics._active_requests._value.get() == initial_active

@patch("app.infrastructure.api.v1.endpoints.status.get_system_health_status")
def test_shared_health_check_implementation_usage(mock_health):
    mock_health.return_value = {
        "all_healthy": True,
        "details": {"database": "healthy", "llm": "healthy", "rag": "healthy", "repository_loader": "healthy"}
    }
    
    from app.main import app
    app.dependency_overrides.clear()
    
    client = TestClient(app)
    
    res1 = client.get("/api/v1/health")
    assert res1.status_code == 200
    
    res2 = client.get("/api/v1/ready")
    assert res2.status_code == 200
    
    assert mock_health.call_count == 2

def test_health_check_extended_payload():
    from app.main import app
    client = TestClient(app)
    
    res = client.get("/api/v1/health")
    assert res.status_code == 200 or res.status_code == 503
    data = res.json()
    assert "application_version" in data
    assert "uptime" in data
    assert "startup_timestamp" in data
    assert data["application_version"] == "1.0.0"
    assert data["uptime"] >= 0
