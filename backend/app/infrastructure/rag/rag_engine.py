from typing import List
from app.domain.models.embedding import SearchResult
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.embedding_port import EmbeddingPort, EmbeddingProvider

class RAGEngine(RAGPort):
    """
    Adapter implementing RAGPort to retrieve semantic context from ChromaDB.
    """
    def __init__(self, vector_store: EmbeddingPort, embedding_provider: EmbeddingProvider) -> None:
        self.store = vector_store
        self.provider = embedding_provider

    async def retrieve_context_chunks(
        self,
        repository_id: str,
        query: str,
        limit: int = 5,
        branch: str = "main"
    ) -> List[SearchResult]:
        # Generate the query vector
        query_vector = self.provider.embed_text(query)
        # Query the vector database (filtering by repo branch)
        return self.store.search(
            repository_id=repository_id,
            branch=branch,
            query_vector=query_vector,
            top_k=limit
        )

    async def check_health(self) -> bool:
        try:
            # Querying metadata stats checks vector database connectivity
            self.store.repository_statistics("health_check_dummy")
            return True
        except Exception:
            return False
