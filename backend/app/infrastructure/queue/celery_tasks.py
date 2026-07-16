import logging
import time
import httpx
from celery import Celery
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.factory import ServiceFactory
from app.use_cases.analysis.runner import AnalysisRunner, AsyncLoopManager
from app.domain.exceptions.agent_exceptions import LLMRateLimitException
from app.domain.models.analysis import ReviewPolicy

logger = logging.getLogger("app.infrastructure.queue.celery_tasks")

# Initialize Celery app instance using the settings config variables
celery_app = Celery("reviewer_tasks")
celery_app.config_from_object("app.infrastructure.queue.celery_config")

@celery_app.task(
    bind=True,
    max_retries=settings.CELERY_MAX_RETRIES,
    name="app.infrastructure.queue.celery_tasks.analyze_repo_task"
)
def analyze_repo_task(
    self,
    analysis_id: str,
    git_url: str = None,
    zip_path: str = None,
    branch: str = None,
    focus_areas: list = None,
    max_issues_per_file: int = None,
    enqueued_at: float = None
) -> None:
    """
    Celery background worker task implementing analysis execution telemetry,
    configurable retry backoffs, and dead-letter queue (DLQ) post-retry failures.
    """
    metrics = ServiceFactory.get_metrics_port()
    
    # 1. Telemetry: record waiting time duration in queue
    if enqueued_at is not None:
        wait_latency = time.time() - enqueued_at
        metrics.record_queue_waiting_time(wait_latency)
        logger.info("Task %s wait latency in queue: %.2fs", analysis_id, wait_latency)

    task_start_time = time.perf_counter()
    try:
        # Resolve ports from unified Application Composition Root ServiceFactory
        orchestrator = ServiceFactory.get_orchestrator()
        db_port = ServiceFactory.get_db_port()
        
        # Instantiate runner execution wrapper
        runner = AnalysisRunner(orchestrator=orchestrator, db_port=db_port)
        
        # Construct policy inside task execution context
        policy = ReviewPolicy(
            focus_areas=focus_areas or [],
            max_issues_per_file=max_issues_per_file if max_issues_per_file is not None else 15
        )
        
        # Run repository review analysis
        runner.execute(
            analysis_id=analysis_id,
            git_url=git_url,
            zip_path=zip_path,
            branch=branch,
            policy=policy
        )
        
        # 2. Telemetry: record task worker execution duration
        duration = time.perf_counter() - task_start_time
        metrics.record_worker_execution_duration(duration)
        logger.info("Task %s completed successfully in %.2fs", analysis_id, duration)
        
    except (LLMRateLimitException, httpx.HTTPError, httpx.TimeoutException, OperationalError) as e:
        # Increment task retries metrics
        metrics.record_task_retry(self.request.retries + 1)
        
        # Calculate countdown backoff using Settings settings
        if settings.CELERY_RETRY_BACKOFF:
            countdown = settings.CELERY_RETRY_DELAY * (2 ** self.request.retries)
        else:
            countdown = settings.CELERY_RETRY_DELAY

        logger.warning(
            "Task %s failed due to retryable exception (%s). Retrying (attempt %d/%d) in %ds...",
            analysis_id, type(e).__name__, self.request.retries + 1, settings.CELERY_MAX_RETRIES, countdown
        )
        
        try:
            raise self.retry(exc=e, countdown=countdown)
        except Exception as retry_exc:
            # Handle post-retry logic when max limit is exceeded
            if "MaxRetriesExceededError" in type(retry_exc).__name__:
                logger.error(
                    "Task %s reached maximum retries limit. Committing permanent failure status and logging DLQ tags.",
                    analysis_id
                )
                
                # Update status DB to FAILED post-retries
                db_port = ServiceFactory.get_db_port()
                async def update_failed():
                    await db_port.update_analysis_progress(
                        analysis_id=analysis_id,
                        status="FAILED",
                        progress_percentage=100.0,
                        error=f"Maximum retries limit exceeded. Original error: {str(e)}"
                    )
                AsyncLoopManager.run(update_failed())
                metrics.record_analysis_failed()
                
            raise retry_exc
            
    except Exception as e:
        # Non-retryable errors: fail fast and record failure metrics immediately
        duration = time.perf_counter() - task_start_time
        metrics.record_worker_execution_duration(duration)
        metrics.record_analysis_failed()
        logger.error("Task %s aborted permanently due to non-retryable error: %s", analysis_id, e)
        raise e
