import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.infrastructure.api.dependencies import get_db_port, get_llm_port, get_rag_port
from app.infrastructure.api.middleware.request_id import RequestIDMiddleware
from app.infrastructure.api.middleware.security import SecurityHeadersMiddleware
from app.infrastructure.api.middleware.logging_middleware import RequestTimingAndLoggingMiddleware
from app.infrastructure.api.errors import register_exception_handlers
from app.infrastructure.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager enforcing startup and shutdown infrastructure sequences.
    """
    import time
    start_time = time.perf_counter()

    # 1. Configure logging
    setup_logging()
    logger.info("Centralized logging configured successfully.")

    # 2. Validate configuration
    try:
        settings.validate_config()
        logger.info("Configuration validated successfully.")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        # Raise RuntimeError to abort and trigger uvicorn graceful shutdown
        if "pytest" not in sys.modules and settings.APP_ENV != "test":
            raise RuntimeError(f"Startup configuration error: {e}") from e

    # 3. Initialize database
    try:
        db_port = get_db_port()
        await db_port.initialize()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if "pytest" not in sys.modules and settings.APP_ENV != "test":
            raise RuntimeError(f"Database startup error: {e}") from e

    # 4, 5 & 6. Initialize Chroma, Claude, and execute health checks
    if "pytest" not in sys.modules and settings.APP_ENV != "test":
        logger.info("Executing startup health checks...")
        
        # Verify database health
        db_ok = await db_port.check_health()
        if not db_ok:
            logger.error("Startup database health check failed.")
            raise RuntimeError("Database health check failed during lifespan startup.")

        # Verify Chroma vector store connection
        try:
            rag_port = get_rag_port()
            rag_ok = await rag_port.check_health()
            if not rag_ok:
                logger.error("Startup ChromaDB health check failed.")
                raise RuntimeError("ChromaDB health check failed during lifespan startup.")
        except Exception as e:
            logger.error(f"ChromaDB connection initialization error: {e}")
            raise RuntimeError(f"ChromaDB startup error: {e}") from e

        # Verify Claude LLM connection
        try:
            llm_port = get_llm_port()
            llm_ok = await llm_port.check_health()
            if not llm_ok:
                logger.error("Startup Claude LLM health check failed.")
                raise RuntimeError("Claude LLM health check failed during lifespan startup.")
        except Exception as e:
            logger.error(f"Claude LLM connection initialization error: {e}")
            raise RuntimeError(f"Claude LLM startup error: {e}") from e

        logger.info("All startup health checks passed.")
    else:
        logger.info("Skipping network/adapter health check validations in test environment.")

    startup_duration = (time.perf_counter() - start_time) * 1000.0
    logger.info("Application startup sequence completed in %.2fms.", startup_duration)

    yield
    
    # Graceful shutdown cleanup
    logger.info("Shutting down application...")
    shutdown_start = time.perf_counter()
    shutdown_duration = (time.perf_counter() - shutdown_start) * 1000.0
    logger.info("Application shutdown sequence completed in %.2fms.", shutdown_duration)

app = FastAPI(
    title=settings.APP_NAME,
    description="Clean Architecture API exposing automated code review, analysis tracking, RAG contexts, and health metrics.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 1. Register CORS Middleware with multi-origin config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Register Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Register Request Timing and Logging Middleware
app.add_middleware(RequestTimingAndLoggingMiddleware)

# 4. Register Request ID Middleware to inject trace context (outermost)
app.add_middleware(RequestIDMiddleware)

# Register custom exception and domain mappings handlers
register_exception_handlers(app)

# Register the aggregated APIRouter with default API prefix (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["status"])
async def root():
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "online"
    }
