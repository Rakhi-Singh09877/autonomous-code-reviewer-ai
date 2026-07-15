from abc import ABC, abstractmethod
from typing import List
from app.domain.models.embedding import SearchResult

class RAGPort(ABC):
    """
    Interface Port defining context lookup operations on indexed vector stores.
    """
    @abstractmethod
    async def retrieve_context_chunks(
        self,
        repository_id: str,
        query: str,
        limit: int = 5,
        branch: str = "main"
    ) -> List[SearchResult]:
        """
        Retrieves matching code chunks from the knowledge base using similarity search.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Verifies vector database and RAG connection health status.
        """
        pass
