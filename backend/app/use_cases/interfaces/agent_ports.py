from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from app.domain.models.parser import ParsedFile
from app.domain.models.analysis import ReviewPolicy
from app.domain.models.report import FileReviewResult
from app.domain.models.embedding import SearchResult

class BaseAgentPort(ABC):
    """
    Base port interface for all codebase analytical agents.
    Provides extensibility for future security, performance, and docs agents.
    """
    @abstractmethod
    async def analyze_file(
        self,
        file_path: Path,
        parsed_file: ParsedFile,
        repo_context: str,
        rag_chunks: List[SearchResult],
        policy: ReviewPolicy
    ) -> FileReviewResult:
        """
        Performs specialized analysis on a file context.
        """
        pass

class ReviewAgentPort(BaseAgentPort):
    """
    Port defining the interface for the primary Code Review Agent.
    """
    pass
