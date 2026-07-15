from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from app.domain.models.repository import Repository

class RepositoryLoaderPort(ABC):
    """
    Interface Port defining methods for repository loading and lifecycle cleanup.
    """
    @abstractmethod
    def load_from_git(self, url: str, branch: Optional[str] = None) -> Repository:
        """
        Clones a Git repository from the given URL and returns a structured Repository domain model.
        """
        pass

    @abstractmethod
    def load_from_zip(self, zip_file: BinaryIO) -> Repository:
        """
        Extracts a ZIP archive file safely and returns a structured Repository domain model.
        """
        pass

    @abstractmethod
    def cleanup(self, repository: Repository) -> None:
        """
        Removes the local directory workspace associated with the given Repository.
        """
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """
        Verifies that the repository loader workspace is accessible and functional.
        """
        pass
