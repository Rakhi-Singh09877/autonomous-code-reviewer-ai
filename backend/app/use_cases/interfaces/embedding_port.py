from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models.embedding import (
    EmbeddingDocument,
    SearchResult,
    KnowledgeBaseStats,
    EmbeddingResult,
)

class EmbeddingProvider(ABC):
    """
    Interface Port defining text embedding generator methods.
    """
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        Generates embedding vector for a single text segment.
        """
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embedding vectors for a batch of text segments.
        """
        pass

class EmbeddingPort(ABC):
    """
    Interface Port defining operations on the ChromaDB Vector Database.
    """
    @abstractmethod
    def upsert_documents(self, repository_id: str, documents: List[EmbeddingDocument]) -> EmbeddingResult:
        """
        Inserts or updates vector records in the database.
        """
        pass

    @abstractmethod
    def delete_repository(self, repository_id: str) -> None:
        """
        Removes all vector index records associated with a repository.
        """
        pass

    @abstractmethod
    def delete_file_documents(self, repository_id: str, relative_path: str) -> None:
        """
        Removes database vector records associated with a single file.
        """
        pass

    @abstractmethod
    def search(self, repository_id: str, branch: str, query_vector: List[float], top_k: int) -> List[SearchResult]:
        """
        Performs vector similarity search filtered by repository and branch.
        """
        pass

    @abstractmethod
    def search_by_file(self, repository_id: str, branch: str, file_path: str, top_k: int) -> List[SearchResult]:
        """
        Performs metadata-filtered search matching a specific file path.
        """
        pass

    @abstractmethod
    def search_by_symbol(self, repository_id: str, branch: str, symbol: str, top_k: int) -> List[SearchResult]:
        """
        Performs metadata-filtered search matching a defined code symbol.
        """
        pass

    @abstractmethod
    def search_by_dependency(self, repository_id: str, branch: str, dependency: str, top_k: int) -> List[SearchResult]:
        """
        Performs metadata-filtered search matching an import dependency.
        """
        pass

    @abstractmethod
    def search_by_language(self, repository_id: str, branch: str, language: str, top_k: int) -> List[SearchResult]:
        """
        Performs metadata-filtered search matching a programming language.
        """
        pass

    @abstractmethod
    def repository_statistics(self, repository_id: str) -> KnowledgeBaseStats:
        """
        Gathers aggregate metrics of chunks and files indexed for a repository.
        """
        pass
