from abc import ABC, abstractmethod
from typing import Optional, List

class JobQueuePort(ABC):
    """
    Port interface defining repository review analysis task dispatch.
    Decouples core API/application layers from task queues or messaging brokers.
    """
    @abstractmethod
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
        Queues an asynchronous repository review task for a worker.
        """
        pass
