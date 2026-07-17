import logging
import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import Response as FastAPIResponse, StreamingResponse

from app.core.config import settings
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.llm_port import LLMPort
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.use_cases.interfaces.metrics_port import MetricsPort

from app.infrastructure.api.dependencies import (
    get_db_port,
    get_llm_port,
    get_rag_port,
    get_loader_port,
    get_metrics_port
)
from app.infrastructure.registry import services_registry
from app.infrastructure.api.schemas.analysis import (
    AnalysisStatusResponse,
    HealthStatusDetail,
    ReadinessStatusDetail
)

logger = logging.getLogger("app.infrastructure.api.endpoints.status")
router = APIRouter()

# Reusable internal health-check function shared by both /health and /ready
async def get_system_health_status(
    db_port: DBPort,
    llm_port: LLMPort,
    rag_port: RAGPort,
    loader_port: RepositoryLoaderPort
) -> dict:
    """
    Evaluates health of all backend adapters concurrently to keep health validation centralized.
    """
    db_ok = await db_port.check_health()
    llm_ok = await llm_port.check_health()
    rag_ok = await rag_port.check_health()
    loader_ok = loader_port.check_health()

    details = {
        "database": "healthy" if db_ok else "unhealthy",
        "llm": "healthy" if llm_ok else "unhealthy",
        "rag": "healthy" if rag_ok else "unhealthy",
        "repository_loader": "healthy" if loader_ok else "unhealthy"
    }
    
    all_healthy = db_ok and llm_ok and rag_ok and loader_ok
    return {
        "all_healthy": all_healthy,
        "details": details
    }

@router.get("/analysis/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: str,
    db_port: DBPort = Depends(get_db_port)
):
    """
    Retrieves the current execution progress, current file, total file count, and errors of an analysis job.
    """
    state = await db_port.get_analysis_state(analysis_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail="Analysis job not found."
        )
    return AnalysisStatusResponse(
        analysis_id=state["analysis_id"],
        status=state["status"],
        progress_percentage=state["progress_percentage"],
        current_file=state["current_file"],
        total_files=state.get("total_files", 0),
        errors=state["errors"]
    )

@router.get("/health", response_model=HealthStatusDetail)
async def health_check(
    response: Response,
    db_port: DBPort = Depends(get_db_port),
    llm_port: LLMPort = Depends(get_llm_port),
    rag_port: RAGPort = Depends(get_rag_port),
    loader_port: RepositoryLoaderPort = Depends(get_loader_port)
):
    """
    Performs system health checks and returns telemetry metadata (version, uptime, startup time).
    """
    health_info = await get_system_health_status(db_port, llm_port, rag_port, loader_port)
    
    if not health_info["all_healthy"]:
        response.status_code = 503  # Service Unavailable
        
    status_str = "healthy" if health_info["all_healthy"] else "unhealthy"
    
    return HealthStatusDetail(
        status=status_str,
        details=health_info["details"],
        application_version=settings.APP_VERSION,
        uptime=services_registry.get_uptime(),
        startup_timestamp=services_registry.startup_timestamp
    )

@router.get("/live")
async def liveness_check():
    """
    Liveness probe verifying that the application container/process is running.
    """
    return {"status": "alive"}

@router.get("/ready", response_model=ReadinessStatusDetail)
async def readiness_check(
    response: Response,
    db_port: DBPort = Depends(get_db_port),
    llm_port: LLMPort = Depends(get_llm_port),
    rag_port: RAGPort = Depends(get_rag_port),
    loader_port: RepositoryLoaderPort = Depends(get_loader_port)
):
    """
    Readiness probe validating dependencies status. Returns 503 if any check fails.
    """
    health_info = await get_system_health_status(db_port, llm_port, rag_port, loader_port)
    
    overall_healthy = health_info["all_healthy"]
    status_str = "ready" if overall_healthy else "not_ready"
    
    if not overall_healthy:
        unhealthy_components = [k for k, v in health_info["details"].items() if v == "unhealthy"]
        logger.error("Readiness check failed. Unhealthy dependencies: %s", ", ".join(unhealthy_components))
        response.status_code = 503
        
    return ReadinessStatusDetail(
        status=status_str,
        details=health_info["details"]
    )

@router.get("/metrics")
def get_metrics(metrics_port: MetricsPort = Depends(get_metrics_port)):
    """
    Exposes metrics for Prometheus scraper with custom content type formats.
    """
    logger.info("Metrics endpoint accessed.")
    metrics_content = metrics_port.generate_prometheus_metrics()
    return FastAPIResponse(
        content=metrics_content,
        media_type="text/plain; version=0.0.4"
    )

@router.get("/events/sse")
async def sse_events(
    analysis_id: str,
    db_port: DBPort = Depends(get_db_port)
):
    """
    Server-Sent Events (SSE) endpoint streaming real-time analysis status updates.
    """
    if not analysis_id or not analysis_id.strip():
        raise HTTPException(
            status_code=400,
            detail="analysis_id query parameter is required."
        )

    try:
        uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid analysis_id. Must be a valid UUID."
        )

    state = await db_port.get_analysis_state(analysis_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail="Analysis job not found."
        )

    async def event_generator():
        try:
            last_status = None
            last_progress = None
            last_current_file = None

            while True:
                current_state = await db_port.get_analysis_state(analysis_id)
                if not current_state:
                    break

                status = current_state["status"]
                progress = current_state["progress_percentage"]
                current_file = current_state["current_file"]

                # Send update if state has changed since last iteration
                if status != last_status or progress != last_progress or current_file != last_current_file:
                    payload = {
                        "analysis_id": current_state["analysis_id"],
                        "status": status,
                        "progress_percentage": progress,
                        "current_file": current_file,
                        "total_files": current_state.get("total_files", 0),
                        "errors": current_state["errors"]
                    }
                    event_data = {
                        "type": "ANALYSIS_PROGRESS",
                        "channel": f"analysis:{analysis_id}",
                        "payload": payload,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

                    last_status = status
                    last_progress = progress
                    last_current_file = current_file

                if status in ("COMPLETED", "FAILED", "CANCELLED"):
                    break

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("SSE client disconnected for analysis_id: %s", analysis_id)
        except Exception as e:
            logger.error("SSE stream error for analysis_id %s: %s", analysis_id, e)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

