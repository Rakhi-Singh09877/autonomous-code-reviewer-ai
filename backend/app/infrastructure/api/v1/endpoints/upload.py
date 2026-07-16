import uuid
import logging
import zipfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException

from app.core.config import settings
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.job_queue_port import JobQueuePort
from app.infrastructure.api.dependencies import get_db_port, get_job_queue
from app.infrastructure.api.schemas.analysis import AnalysisInitiateResponse

logger = logging.getLogger("app.infrastructure.api.endpoints.upload")
router = APIRouter()

@router.post("/analyze", response_model=AnalysisInitiateResponse, status_code=202)
async def analyze_repository(
    git_url: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    focus_areas: Optional[str] = Form(None),  # Comma-separated list
    max_issues_per_file: Optional[int] = Form(None),
    queue: JobQueuePort = Depends(get_job_queue),
    db_port: DBPort = Depends(get_db_port)
):
    """
    Initiates asynchronous code review analysis for a Git URL or uploaded ZIP file.
    Queues tasks onto the persistent distributed task broker queue.
    """
    # 1. Input validations
    if not git_url and not file:
        raise HTTPException(
            status_code=400,
            detail="Either git_url or file upload must be provided."
        )
    if git_url and file:
        raise HTTPException(
            status_code=400,
            detail="Provide either git_url or file upload, not both."
        )
        
    zip_disk_path = None
    if file:
        if not file.filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail="Only ZIP archives are supported."
            )
            
        # Write file in chunks to temporary storage to optimize memory usage
        temp_dir = Path(settings.TEMP_STORAGE_PATH)
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file_name = f"upload_{uuid.uuid4()}.zip"
        zip_disk_path = str(temp_dir / temp_file_name)
        
        try:
            with open(zip_disk_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    f.write(chunk)
        except Exception as e:
            if Path(zip_disk_path).exists():
                Path(zip_disk_path).unlink()
            logger.error("Failed to save uploaded ZIP to disk: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save uploaded file: {e}"
            )
            
        # Validate ZIP archive structure integrity
        try:
            with zipfile.ZipFile(zip_disk_path, "r") as archive:
                bad_file = archive.testzip()
                if bad_file:
                    if Path(zip_disk_path).exists():
                        Path(zip_disk_path).unlink()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid ZIP archive: bad file {bad_file} inside archive"
                    )
        except zipfile.BadZipFile as e:
            if Path(zip_disk_path).exists():
                Path(zip_disk_path).unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ZIP archive structure: {e}"
            )

    # Parse review policy fields
    policy_focus = [f.strip() for f in focus_areas.split(",")] if focus_areas else []
    max_issues = max_issues_per_file if max_issues_per_file is not None else 15

    analysis_id = str(uuid.uuid4())
    
    # Write initial analysis entry to database
    try:
        await db_port.create_analysis(analysis_id)
    except Exception as e:
        if zip_disk_path and Path(zip_disk_path).exists():
            Path(zip_disk_path).unlink()
        logger.error("Failed to create analysis run tracking in DB: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize analysis job."
        )

    # Enqueue analysis task in queue
    try:
        queue.enqueue_analysis(
            analysis_id=analysis_id,
            git_url=git_url,
            zip_path=zip_disk_path,
            branch=branch,
            focus_areas=policy_focus,
            max_issues_per_file=max_issues
        )
    except Exception as e:
        logger.error("Failed to enqueue analysis task into queue: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue analysis task: {e}"
        )

    return AnalysisInitiateResponse(analysis_id=analysis_id, status="PENDING")
