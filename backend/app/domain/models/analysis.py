from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

class AgentType(str, Enum):
    REVIEW = "REVIEW"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    DOCUMENTATION = "DOCUMENTATION"

class PromptVersion(str, Enum):
    REVIEW_V1 = "review_v1"
    SECURITY_V1 = "security_v1"
    PERFORMANCE_V1 = "performance_v1"
    DOCUMENTATION_V1 = "documentation_v1"

@dataclass
class ReviewPolicy:
    """
    Domain model representing rules and guidelines for code analysis.
    """
    rules: List[str] = field(default_factory=list)
    custom_instructions: Optional[str] = None
    focus_areas: List[str] = field(default_factory=list)
    max_issues_per_file: int = 15
    prompt_version: PromptVersion = PromptVersion.REVIEW_V1
