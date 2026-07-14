from abc import ABC, abstractmethod
from pathlib import Path
from app.domain.models.language import LanguageDetectionResult, WorkspaceLanguageProfile

class LanguageDetectorPort(ABC):
    """
    Interface Port defining methods for single file and workspace language detection.
    """
    @abstractmethod
    def detect_file_language(self, file_path: Path) -> LanguageDetectionResult:
        """
        Detects the programming language and metadata of a single file.
        """
        pass

    @abstractmethod
    def analyze_workspace(self, workspace_path: Path) -> WorkspaceLanguageProfile:
        """
        Traverses a workspace and aggregates language detection metrics.
        """
        pass
