from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.domain.models.report import RepositoryReviewReport

class DBPort(ABC):
    """
    Interface Port defining database operations for review run analysis tracking and health checks.
    """
    @abstractmethod
    async def create_analysis(self, analysis_id: str, repository_id: Optional[str] = None) -> None:
        """Initializes a new analysis state inside the database."""
        pass

    @abstractmethod
    async def update_analysis_progress(
        self,
        analysis_id: str,
        status: str,
        progress_percentage: float,
        current_file: Optional[str] = None,
        error: Optional[str] = None,
        total_files: Optional[int] = None
    ) -> None:
        """Updates the status and incremental progress of an ongoing analysis run."""
        pass

    @abstractmethod
    async def save_analysis_report(self, analysis_id: str, report: RepositoryReviewReport) -> None:
        """Stores the completed analysis review report."""
        pass

    @abstractmethod
    async def get_analysis_state(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the current status, progress, errors, and metadata of a specific analysis run."""
        pass

    @abstractmethod
    async def get_analysis_report(self, analysis_id: str) -> Optional[RepositoryReviewReport]:
        """Retrieves the aggregated RepositoryReviewReport for a completed analysis run."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Checks the connection health of the underlying database."""
        pass
