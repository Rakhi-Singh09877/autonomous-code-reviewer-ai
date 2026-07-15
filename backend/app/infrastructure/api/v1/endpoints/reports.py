import logging
from fastapi import APIRouter, Depends, HTTPException
from app.use_cases.interfaces.db_port import DBPort
from app.infrastructure.api.dependencies import get_db_port
from app.domain.models.report import RepositoryReviewReport

logger = logging.getLogger("app.infrastructure.api.endpoints.reports")
router = APIRouter()

@router.get("/analysis/{analysis_id}/report", response_model=RepositoryReviewReport)
async def get_analysis_report(
    analysis_id: str,
    db_port: DBPort = Depends(get_db_port)
):
    """
    Retrieves the completed RepositoryReviewReport for a finished review run.
    """
    state = await db_port.get_analysis_state(analysis_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail="Analysis job not found."
        )
        
    if state["status"] != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis report is not ready. Current status: {state['status']}"
        )
        
    report = await db_port.get_analysis_report(analysis_id)
    if not report:
        raise HTTPException(
            status_code=500,
            detail="Analysis report could not be loaded."
        )
        
    return report
