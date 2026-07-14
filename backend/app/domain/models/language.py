from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

@dataclass
class LanguageDetectionResult:
    """
    Domain model representing the language detection outcome for a single file.
    """
    file_path: Path
    language: str
    confidence: float
    detection_method: str  # "binary", "extension", "shebang", "signature", "unknown"
    extension: str
    encoding: str
    file_size: int
    is_binary: bool

@dataclass
class WorkspaceLanguageProfile:
    """
    Domain model representing the aggregated language profile of a workspace/repository.
    """
    total_files: int
    source_files: int
    binary_files: int
    unknown_files: int
    languages: Dict[str, Dict[str, Any]]  # format: {"Python": {"count": 10, "percentage": 0.5}}
