import io
import json
import logging
import uuid
import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure app directory is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import Settings
from app.core.logging import JsonFormatter, PlainFormatter, request_id_ctx_var, setup_logging
from app.infrastructure.api.middleware.request_id import RequestIDMiddleware
from app.infrastructure.database.repository import SQLAlchemyDBAdapter
from app.main import lifespan

def test_json_formatter_formatting():
    # Setup log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message format",
        args=None,
        exc_info=None
    )
    # Set request id in context variable
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
    
    # 1. Automatic generation
    res = client.get("/test")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    generated_id = res.headers["X-Request-ID"]
    assert res.json()["current_request_id"] == generated_id
    
    # 2. Propagation of client provided X-Request-ID
    client_id = str(uuid.uuid4())
    res = client.get("/test", headers={"X-Request-ID": client_id})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == client_id
    assert res.json()["current_request_id"] == client_id

def test_provider_driven_config_validation():
    # 1. Anthropic model requires ANTHROPIC_API_KEY
    cfg = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="",
        EMBEDDING_PROVIDER="local"
    )
    with pytest.raises(ValueError) as exc:
        cfg.validate_config(force=True)
    assert "ANTHROPIC_API_KEY is required" in str(exc.value)

    # 2. OpenAI Embedding requires OPENAI_API_KEY
    cfg = Settings(
        LLM_PROVIDER="local",
        EMBEDDING_PROVIDER="openai",
        OPENAI_API_KEY=""
    )
    with pytest.raises(ValueError) as exc:
        cfg.validate_config(force=True)
    assert "OPENAI_API_KEY is required" in str(exc.value)

    # 3. Local LLM and Embedding requires no keys
    cfg = Settings(
        LLM_PROVIDER="local",
        EMBEDDING_PROVIDER="local",
        OPENAI_API_KEY="",
        ANTHROPIC_API_KEY=""
    )
    # Should not raise exception
    cfg.validate_config(force=True)

@pytest.mark.asyncio
async def test_database_port_initialize():
    # Use temporary sqlite database file
    db = SQLAlchemyDBAdapter(database_url="sqlite:///:memory:")
    # Initialize database
    await db.initialize()
    # Confirm DB can query
    assert await db.check_health() is True

@pytest.mark.asyncio
async def test_lifespan_startup_failures_raise_runtime_error():
    app = FastAPI()
    
    # Setup mocks for dependencies
    mock_db = MagicMock()
    mock_db.initialize = AsyncMock()
    mock_db.check_health = AsyncMock(return_value=False) # DB health check fails
    
    mock_llm = MagicMock()
    mock_llm.check_health = AsyncMock(return_value=True)
    
    mock_rag = MagicMock()
    mock_rag.check_health = AsyncMock(return_value=True)
    
    # Safely simulate non-test environment modules
    modules_copy = sys.modules.copy()
    if "pytest" in modules_copy:
        del modules_copy["pytest"]
    
    # Overwrite lifespan dependencies inside test app context
    with patch("sys.modules", modules_copy), \
         patch("app.main.get_db_port", return_value=mock_db), \
         patch("app.main.get_llm_port", return_value=mock_llm), \
         patch("app.main.get_rag_port", return_value=mock_rag), \
         patch("app.main.setup_logging"), \
         patch("app.core.config.Settings.validate_config"):
         
         # When database health check fails, lifespan must raise RuntimeError
         with pytest.raises(RuntimeError) as exc:
             async with lifespan(app):
                 pass
         assert "Database health check failed" in str(exc.value)
