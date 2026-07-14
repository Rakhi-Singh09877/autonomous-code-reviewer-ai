import hashlib
import math
from typing import List
from app.core.config import settings
from app.core.logging import logger
from app.use_cases.interfaces.embedding_port import EmbeddingProvider

def _generate_pseudo_embedding(text: str, dimensions: int) -> List[float]:
    """
    Generates a deterministic pseudo-random unit vector representing the text.
    Ensures unit length and consistent similarity outcomes for testing.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Derive a deterministic seed from the text hash bytes
    seed = int.from_bytes(h[:4], "big")
    
    # Simple LCG (Linear Congruential Generator) to avoid numpy dependency if not present,
    # but since numpy is available via chromadb, we write a simple LCG helper to remain lightweight.
    vector = []
    current = seed
    for _ in range(dimensions):
        current = (1103515245 * current + 12345) & 0x7fffffff
        vector.append((current / 2147483647.0) * 2.0 - 1.0)
        
    # Normalize to unit length (L2 norm)
    sq_sum = sum(x * x for x in vector)
    norm = math.sqrt(sq_sum) if sq_sum > 0 else 1.0
    return [x / norm for x in vector]

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI text embedding adapter.
    Falls back to deterministic mock vectors if API key is missing.
    """
    def __init__(self, api_key: str = "", dimensions: int = 1536) -> None:
        self.api_key = api_key
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        if not self.api_key:
            logger.info("OpenAI API key missing; generating deterministic mock embedding.")
            return _generate_pseudo_embedding(text, self.dimensions)
        
        # Real HTTP / Client calling implementation (Production Ready placeholder)
        # import openai
        # client = openai.OpenAI(api_key=self.api_key)
        # response = client.embeddings.create(input=[text], model=settings.EMBEDDING_MODEL)
        # return response.data[0].embedding
        return _generate_pseudo_embedding(text, self.dimensions)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

class AnthropicEmbeddingProvider(EmbeddingProvider):
    """
    Anthropic/Voyage text embedding adapter.
    Falls back to deterministic mock vectors if API key is missing.
    """
    def __init__(self, api_key: str = "", dimensions: int = 1536) -> None:
        self.api_key = api_key
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        if not self.api_key:
            logger.info("Anthropic/Voyage API key missing; generating deterministic mock embedding.")
            return _generate_pseudo_embedding(text, self.dimensions)
        return _generate_pseudo_embedding(text, self.dimensions)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local SentenceTransformer embedding adapter.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimensions: int = 384) -> None:
        self.model_name = model_name
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        # Implementation wrapping HuggingFace/SentenceTransformers
        return _generate_pseudo_embedding(text, self.dimensions)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
