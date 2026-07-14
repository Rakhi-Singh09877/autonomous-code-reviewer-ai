from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

@dataclass
class CodeEntity:
    """
    Domain model representing a class, function, or method entity inside a file.
    """
    name: str
    type: str  # "class", "function", "method"
    signature: str
    start_line: int
    end_line: int
    docstring: Optional[str]
    source_range: Tuple[int, int]  # (start_char_index, end_char_index)
    visibility: str  # "public", "private", "protected", "internal"
    decorators: List[str] = field(default_factory=list)
    parent_class: Optional[str] = None

@dataclass
class ParsedFile:
    """
    Domain model representing the structural parsing outcome for a single file.
    """
    file_path: Path
    relative_path: str
    module_name: str
    package_name: str
    language: str
    imports: List[str]
    classes: List[CodeEntity]
    functions: List[CodeEntity]
    todos: List[Dict[str, Any]]  # [{"line": int, "text": str}]
    line_count: int
    char_count: int
    parse_status: str  # "success", "partial_failure", "unsupported"
    symbols: List[str]
    dependencies: List[str]
    complexity_score: int
    has_tests: bool
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    # RAG chunks layout: [{"id": str, "entity_name": str, "language": str, "text": str, "metadata": dict}]

@dataclass
class CodebaseStructure:
    """
    Domain model representing the aggregated parse information of the entire repository.
    """
    files: List[ParsedFile]
    total_files: int
    parsed_files: int
    failed_files: int
    unsupported_files: int
    language_statistics: Dict[str, Any]
