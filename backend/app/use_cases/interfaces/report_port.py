from abc import ABC, abstractmethod
from app.domain.models.report import RepositoryReviewReport

class ReportPort(ABC):
    """
    Interface Port defining report generation capabilities.
    """
    @abstractmethod
    def generate_report(self, report: RepositoryReviewReport) -> str:
        """
        Generates and serializes the review report into formatted representation.
        """
        pass
