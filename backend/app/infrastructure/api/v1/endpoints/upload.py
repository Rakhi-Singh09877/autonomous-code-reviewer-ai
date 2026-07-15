import uuid
import logging
import zipfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, BackgroundTasks, HTTPException

from app.core.config import settings
from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator
from app.use_cases.interfaces.db_port import DBPort
from app.domain.models.analysis import ReviewPolicy
from app.infrastructure.api.dependencies import get_orchestrator, get_db_port
from app.infrastructure.api.schemas.analysis import AnalysisInitiateResponse

logger = logging.getLogger("app.infrastructure.api.endpoints.upload")
router = APIRouter()

async def run_analysis_background(
    analysis_id: str,
    orchestrator: RepositoryAnalysisOrchestrator,
    db_port: DBPort,
    git_url: Optional[str] = None,
    zip_path: Optional[str] = None,
    branch: Optional[str] = None,
    policy: Optional[ReviewPolicy] = None
) -> None:
    """
    Background worker function updating analysis runs state in DB and cleaning up zip resources.
    """
    async def progress_callback(
        status: str,
        progress: float,
        current_file: Optional[str],
        error: Optional[str],
        total_files: Optional[int] = None
    ):
        await db_port.update_analysis_progress(
            analysis_id=analysis_id,
            status=status,
            progress_percentage=progress,
            current_file=current_file,
            error=error,
            total_files=total_files
        )

    zip_file = None
    try:
        if zip_path:
            zip_file = open(zip_path, "rb")
        
        report = await orchestrator.analyze_repository(
            git_url=git_url,
            zip_file=zip_file,
            branch=branch,
            policy=policy,
            progress_callback=progress_callback
        )
        
        # Save completed report and update state to COMPLETED
        await db_port.save_analysis_report(analysis_id, report)
        logger.info("Background analysis completed successfully for run: %s", analysis_id)
        
    except Exception as e:
        logger.error("Error executing background analysis run %s: %s", analysis_id, e, exc_info=True)
        await db_port.update_analysis_progress(
            analysis_id=analysis_id,
            status="FAILED",
            progress_percentage=100.0,
            error=str(e)
        )
    finally:
        if zip_file:
            try:
                zip_file.close()
            except Exception as e:
                logger.error("Failed to close ZIP file: %s", e)
        if zip_path:
            try:
                p = Path(zip_path)
                if p.exists():
                    p.unlink()
                    logger.info("Temporary uploaded zip file cleaned up: %s", zip_path)
            except Exception as e:
                logger.error("Failed to clean up temporary ZIP file %s: %s", zip_path, e)

@router.post("/analyze", response_model=AnalysisInitiateResponse, status_code=202)
async def analyze_repository(
    background_tasks: BackgroundTasks,
    git_url: Optional[str] = Form(None),
    branch: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    focus_areas: Optional[str] = Form(None),  # Comma-separated list
    max_issues_per_file: Optional[int] = Form(None),
    orchestrator: RepositoryAnalysisOrchestrator = Depends(get_orchestrator),
    db_port: DBPort = Depends(get_db_port)
):
    """
    Initiates asynchronous code review analysis for a Git URL or uploaded ZIP file.
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
    policy = ReviewPolicy(
        focus_areas=policy_focus,
        max_issues_per_file=max_issues_per_file if max_issues_per_file is not None else 15
    )

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

    # 2. Add background task execution
    background_tasks.add_task(
        run_analysis_background,
        analysis_id=analysis_id,
        orchestrator=orchestrator,
        db_port=db_port,
        git_url=git_url,
        zip_path=zip_disk_path,
        branch=branch,
        policy=policy
    )

    return AnalysisInitiateResponse(analysis_id=analysis_id, status="PENDING")
