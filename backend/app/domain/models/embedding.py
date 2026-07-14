from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional

@dataclass
class ChunkMetadata:
    """
    Domain model representing structural search metadata linked to a specific code chunk.
    """
    symbols: List[str]
    dependencies: List[str]
    complexity_score: int
    relative_path: str
    package_name: str
    start_line: int
    end_line: int
    repository_name: str
    branch: str
    language: str
    entity_type: str
    parser_version: str
    indexed_at: str  # ISO 8601 string format

@dataclass
class EmbeddingDocument:
    """
    Domain model representing a single text chunk loaded with embedding features and an MCP-compatible resource URI.
    """
    id: str
    repository_id: str
    file_path: str
    module_name: str
    entity_name: str
    entity_type: str
    language: str
    text: str
    metadata: ChunkMetadata
    resource_uri: str
    embedding: Optional[List[float]] = None

@dataclass
class SearchResult:
    """
    Domain model returning the result of a similarity vector search.
    """
    document: EmbeddingDocument
    score: float
    distance: float
    matched_metadata: Dict[str, Any]

@dataclass
class KnowledgeBaseStats:
    """
    Domain model summarizing repository indexing status and database metrics.
    """
    indexed_files: int
    indexed_chunks: int
    embedding_model: str
    last_indexed_at: str
    average_chunk_size: float
    storage_size: int  # Estimated storage size in bytes

@dataclass
class EmbeddingResult:
    """
    Domain model representing the metrics of a database upsert indexing task.
    """
    inserted_count: int
    updated_count: int
    deleted_count: int
    failed_files: List[str] = field(default_factory=list)
