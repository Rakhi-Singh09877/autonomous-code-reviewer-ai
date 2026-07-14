from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.domain.models.report import RepositoryReviewReport

class MCPPort(ABC):
    """
    Interface Port outlining Model Context Protocol mappings.
    """
    @abstractmethod
    def map_report_to_resources(self, report: RepositoryReviewReport) -> List[Dict[str, Any]]:
        """
        Translates finding models into MCP resources schemas.
        """
        pass
