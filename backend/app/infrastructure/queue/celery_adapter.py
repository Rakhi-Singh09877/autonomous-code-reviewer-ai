import time
from typing import Optional, List
from app.use_cases.interfaces.job_queue_port import JobQueuePort
from app.infrastructure.queue.celery_tasks import analyze_repo_task

class CeleryJobQueueAdapter(JobQueuePort):
    """
    Adapter implementing JobQueuePort by dispatching tasks to Redis via Celery delay hooks.
    """
    def enqueue_analysis(
        self,
        analysis_id: str,
        git_url: Optional[str] = None,
        zip_path: Optional[str] = None,
        branch: Optional[str] = None,
        focus_areas: Optional[List[str]] = None,
        max_issues_per_file: Optional[int] = None
    ) -> None:
        """
        Calculates enqueued_at time and dispatches celery task.
        """
        analyze_repo_task.delay(
            analysis_id=analysis_id,
            git_url=git_url,
            zip_path=zip_path,
            branch=branch,
            focus_areas=focus_areas,
            max_issues_per_file=max_issues_per_file,
            enqueued_at=time.time()
        )
