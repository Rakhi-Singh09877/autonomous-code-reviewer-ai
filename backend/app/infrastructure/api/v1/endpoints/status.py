import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.llm_port import LLMPort
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.infrastructure.api.dependencies import get_db_port, get_llm_port, get_rag_port, get_loader_port
from app.infrastructure.api.schemas.analysis import AnalysisStatusResponse, HealthStatusDetail

logger = logging.getLogger("app.infrastructure.api.endpoints.status")
router = APIRouter()

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
    Performs real-time health checks on LLM, RAG index, Database, and Workspace storage.
    """
    # 1. Database check
    db_ok = await db_port.check_health()
    
    # 2. LLM check
    llm_ok = await llm_port.check_health()
    
    # 3. RAG/Vector DB check
    rag_ok = await rag_port.check_health()
    
    # 4. Storage / Repository Loader writable check via loader port
    loader_ok = loader_port.check_health()

    details = {
        "database": "healthy" if db_ok else "unhealthy",
        "llm": "healthy" if llm_ok else "unhealthy",
        "rag": "healthy" if rag_ok else "unhealthy",
        "repository_loader": "healthy" if loader_ok else "unhealthy"
    }
    
    overall_healthy = db_ok and llm_ok and rag_ok and loader_ok
    status_str = "healthy" if overall_healthy else "unhealthy"
    
    if not overall_healthy:
        response.status_code = 503  # Service Unavailable
        
    return HealthStatusDetail(status=status_str, details=details)
