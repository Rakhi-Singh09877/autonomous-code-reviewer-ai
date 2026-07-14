from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from uuid import UUID

class ReviewIssueSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReviewIssueCategory(str, Enum):
    CODE_QUALITY = "CODE_QUALITY"
    BUG_DETECTION = "BUG_DETECTION"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    BEST_PRACTICES = "BEST_PRACTICES"
    MAINTAINABILITY = "MAINTAINABILITY"
    CODE_SMELLS = "CODE_SMELLS"
    COMPLEXITY = "COMPLEXITY"

@dataclass
class ReviewIssue:
    """
    Domain model representing an identified code quality warning or error.
    """
    id: UUID
    file_path: Path
    line_start: int
    line_end: int
    category: ReviewIssueCategory
    severity: ReviewIssueSeverity
    confidence: float  # Value between 0.0 and 1.0
    description: str
    explanation: str
    suggested_fix: str
    snippet: str
