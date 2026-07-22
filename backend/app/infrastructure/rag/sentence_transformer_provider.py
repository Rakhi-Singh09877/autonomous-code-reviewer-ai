"""
Local SentenceTransformer embedding provider.

Uses ``sentence-transformers`` to run embedding inference entirely on the
local machine — no paid API, no network calls after the initial model
download.  The default model is ``all-MiniLM-L6-v2`` (384-dimensional
embeddings, fast, and widely used for semantic search).

Architecture note:
    This adapter implements ``EmbeddingProvider`` (the same interface
    previously satisfied by ``OpenAIEmbeddingProvider``).  Consumers
    (``ChromaVectorStore``, ``RAGEngine``, ``ServiceFactory``) require
    zero changes — only the composition root wiring changes.
"""

import logging
from typing import List

from app.core.config import settings
from app.use_cases.interfaces.embedding_port import EmbeddingProvider

logger = logging.getLogger("app.infrastructure.rag.sentence_transformer_provider")


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding adapter backed by a ``SentenceTransformer`` model.

    The model is loaded lazily on first use and reused as a singleton
    class-level reference so that it is never reloaded across requests.

    Raises
    ------
    RuntimeError
        If the model cannot be downloaded / loaded at first use.
    """

    # Singleton model shared across all instances (loaded once, reused forever).
    _model = None
    _model_lock = False  # simple guard to prevent concurrent loads

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimensions: int = 384) -> None:
        """
        Parameters
        ----------
        model_name : str
            HuggingFace sentence-transformers model identifier.
        dimensions : int
            Expected output embedding dimensionality (informational).
        """
        self._model_name = model_name or settings.LOCAL_EMBEDDING_MODEL
        self._dimensions = dimensions or settings.EMBEDDING_DIMENSIONS

    # ------------------------------------------------------------------
    # EmbeddingProvider interface
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> List[float]:
        """
        Generate a single embedding vector for **text**.

        Returns a Python ``list[float]`` of length ``EMBEDDING_DIMENSIONS``.
        """
        model = self._get_model()
        # SentenceTransformer.encode returns numpy.ndarray; convert to list.
        embedding = model.encode([text], show_progress_bar=False, convert_to_numpy=True)
        return embedding[0].tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-encode a list of strings.

        Batching is significantly faster than calling ``embed_text`` in
        a loop because the model can parallelise tokenisation and matrix
        operations.
        """
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _get_model(cls):
        """
        Lazily load and cache the SentenceTransformer model.

        The model is stored at the class level so that every instance of
        ``SentenceTransformerEmbeddingProvider`` shares the same
        in-memory copy — no redundant GPU/CPU memory usage.
        """
        if cls._model is not None:
            return cls._model

        if cls._model_lock:
            # Another thread is loading; busy-wait briefly (rare path).
            import time
            for _ in range(60):  # at most 60 seconds
                if cls._model is not None:
                    return cls._model
                time.sleep(1)
            raise RuntimeError(
                "SentenceTransformer model load timed out — another thread may be stuck."
            )

        cls._model_lock = True
        try:
            # Import here so that the module is importable even without
            # sentence-transformers installed (useful in test environments
            # that mock the provider).
            from sentence_transformers import SentenceTransformer

            model_name = cls._get_model_name_static()
            logger.info(
                "Loading local SentenceTransformer model '%s' (first use) — "
                "this may download ~80 MB on the first run.",
                model_name,
            )
            cls._model = SentenceTransformer(model_name)
            logger.info(
                "SentenceTransformer model '%s' loaded successfully.",
                model_name,
            )
            return cls._model
        except Exception as exc:
            cls._model_lock = False
            logger.exception(
                "Failed to load SentenceTransformer model '%s'.",
                cls._get_model_name_static(),
            )
            raise RuntimeError(
                f"Could not load local embedding model "
                f"'{cls._get_model_name_static()}': {exc}"
            ) from exc

    @staticmethod
    def _get_model_name_static() -> str:
        """Resolve the model name from settings (avoids instance attr access in classmethod)."""
        return getattr(settings, "LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
