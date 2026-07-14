from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from uuid import UUID
from app.domain.models.issue import ReviewIssue

@dataclass
class TokenUsageMetadata:
    """
    Domain model tracking token usage and cost metrics of LLM execution.
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, other: "TokenUsageMetadata") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        self.estimated_cost_usd += other.estimated_cost_usd

@dataclass
class FileReviewResult:
    """
    Domain model representing the code review outcome for a single file.
    """
    file_path: Path
    issues: List[ReviewIssue] = field(default_factory=list)
    score: int = 100
    review_time_sec: float = 0.0
    token_usage: TokenUsageMetadata = field(default_factory=TokenUsageMetadata)

@dataclass
class RepositoryReviewReport:
    """
    Domain model representing the aggregated codebase review report.
    """
    id: UUID
    repository_id: UUID
    created_at: datetime
    files_reviewed: int
    total_issues: int
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    average_score: float = 100.0
    file_results: List[FileReviewResult] = field(default_factory=list)
    token_usage: TokenUsageMetadata = field(default_factory=TokenUsageMetadata)
