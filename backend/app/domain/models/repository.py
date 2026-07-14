from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

class RepositorySourceType(str, Enum):
    GIT = "GIT"
    ZIP = "ZIP"

class Repository:
    """
    Domain entity representing a cloned or extracted code repository in the workspace.
    """
    def __init__(
        self,
        local_path: Path,
        source_type: RepositorySourceType,
        file_count: int,
        total_size_bytes: int,
        id: Optional[UUID] = None,
        branch: Optional[str] = None,
        git_url: Optional[str] = None,
    ):
        self.id = id or uuid4()
        self.local_path = local_path
        self.source_type = source_type
        self.file_count = file_count
        self.total_size_bytes = total_size_bytes
        self.branch = branch
        self.git_url = git_url

    def __repr__(self) -> str:
        return (
            f"Repository(id={self.id}, path={self.local_path}, "
            f"type={self.source_type.value}, files={self.file_count}, "
            f"size={self.total_size_bytes}B)"
        )
