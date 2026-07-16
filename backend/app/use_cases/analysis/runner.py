import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, Any

from app.core.config import settings
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator
from app.domain.models.analysis import ReviewPolicy

logger = logging.getLogger("app.use_cases.analysis.runner")

class IdempotencyGuard:
    """
    Application service verifying analysis run state to prevent duplicate runs
    and recovering stale PROCESSING scans using setting timeouts.
    """
    def __init__(self, db_port: DBPort) -> None:
        self.db_port = db_port

    async def validate_and_claim(self, analysis_id: str) -> Tuple[bool, str]:
        """
        Asserts if the analysis should run.
        Returns: Tuple[should_proceed, reason_or_error_string]
        """
        state = await self.db_port.get_analysis_state(analysis_id)
        if not state:
            return True, ""

        status = state.get("status", "PENDING")
        if status == "COMPLETED":
            return False, "Analysis has already completed successfully."

        if status == "PROCESSING":
            # Check updated_at to determine if job is stale/crashed
            updated_at_val = state.get("updated_at")
            if updated_at_val:
                try:
                    if isinstance(updated_at_val, str):
                        updated_at = datetime.fromisoformat(updated_at_val.replace("Z", "+00:00"))
                    else:
                        updated_at = updated_at_val

                    # Calculate elapsed seconds since last state update
                    elapsed = (datetime.now(timezone.utc) - updated_at).total_seconds()
                    if elapsed > settings.JOB_TIMEOUT_SECONDS:
                        logger.warning(
                            "Recovering stale PROCESSING run %s. Elapsed duration: %.1fs exceeds timeout limit of %ds.",
                            analysis_id, elapsed, settings.JOB_TIMEOUT_SECONDS
                        )
                        return True, "Recovering stale PROCESSING job."
                except Exception as e:
                    logger.error("Failed to parse state updated_at timestamp: %s", e)

            return False, "Analysis is currently processing."

        return True, ""

class JobStatusManager:
    """
    Application service managing db status transitions.
    """
    def __init__(self, db_port: DBPort) -> None:
        self.db_port = db_port

    async def update_status(
        self,
        analysis_id: str,
        status: str,
        progress: float,
        current_file: Optional[str] = None,
        error: Optional[str] = None,
        total_files: Optional[int] = None
    ) -> None:
        await self.db_port.update_analysis_progress(
            analysis_id=analysis_id,
            status=status,
            progress_percentage=progress,
            current_file=current_file,
            error=error,
            total_files=total_files
        )

    async def save_report(self, analysis_id: str, report: Any) -> None:
        await self.db_port.save_analysis_report(analysis_id, report)

class AsyncLoopManager:
    """
    Application service running asynchronous coroutines within synchronous runner contexts.
    """
    @staticmethod
    def run(coro):
        """
        Runs coroutine using new or existing asyncio loop.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)

class AnalysisRunner:
    """
    Application service coordinating task startup, idempotency, updates, and orchestrator execution.
    Exposed exclusively to worker thread context.
    """
    def __init__(
        self,
        orchestrator: RepositoryAnalysisOrchestrator,
        db_port: DBPort
    ) -> None:
        self.orchestrator = orchestrator
        self.db_port = db_port
        self.idempotency_guard = IdempotencyGuard(db_port)
        self.status_manager = JobStatusManager(db_port)

    def execute(
        self,
        analysis_id: str,
        git_url: Optional[str] = None,
        zip_path: Optional[str] = None,
        branch: Optional[str] = None,
        policy: Optional[ReviewPolicy] = None
    ) -> None:
        """
        Runs complete analysis workflow inside Event Loop wrapper.
        """
        AsyncLoopManager.run(self._execute_async(analysis_id, git_url, zip_path, branch, policy))

    async def _execute_async(
        self,
        analysis_id: str,
        git_url: Optional[str] = None,
        zip_path: Optional[str] = None,
        branch: Optional[str] = None,
        policy: Optional[ReviewPolicy] = None
    ) -> None:
        # 1. Verify and claim idempotency
        should_run, reason = await self.idempotency_guard.validate_and_claim(analysis_id)
        if not should_run:
            logger.info("Skipping task run %s: %s", analysis_id, reason)
            return

        # 2. Transition state to PROCESSING
        logger.info("Setting task status to PROCESSING for analysis run: %s", analysis_id)
        await self.status_manager.update_status(
            analysis_id=analysis_id,
            status="PROCESSING",
            progress=0.0,
            current_file="Initializing scan..."
        )

        async def progress_callback(
            status: str,
            progress: float,
            current_file: Optional[str],
            error: Optional[str],
            total_files: Optional[int] = None
        ):
            await self.status_manager.update_status(
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

            # 3. Invoke scan orchestration
            report = await self.orchestrator.analyze_repository(
                git_url=git_url,
                zip_file=zip_file,
                branch=branch,
                policy=policy,
                progress_callback=progress_callback
            )

            # 4. Save analysis report
            await self.status_manager.save_report(analysis_id, report)
            logger.info("Completed analysis task execution for run: %s", analysis_id)

        except Exception as e:
            logger.error("Error executing repository scan %s: %s", analysis_id, e, exc_info=True)
            await self.status_manager.update_status(
                analysis_id=analysis_id,
                status="FAILED",
                progress=100.0,
                error=str(e)
            )
            raise e
        finally:
            if zip_file:
                try:
                    zip_file.close()
                except Exception as e:
                    logger.error("Failed to close uploaded zip file: %s", e)
