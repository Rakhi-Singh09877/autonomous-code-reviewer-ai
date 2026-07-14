import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import chromadb

from app.core.config import settings
from app.core.logging import logger
from app.domain.models.embedding import (
    EmbeddingDocument,
    ChunkMetadata,
    SearchResult,
    KnowledgeBaseStats,
    EmbeddingResult,
)
from app.use_cases.interfaces.embedding_port import EmbeddingPort, EmbeddingProvider

class ChromaVectorStore(EmbeddingPort):
    """
    Adapter implementing EmbeddingPort using ChromaDB client.
    """

    def __init__(self, embedding_provider: EmbeddingProvider, persist_dir: Optional[str] = None):
        self.provider = embedding_provider
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        
        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB initialized at: {self.persist_dir}")

    def upsert_documents(self, repository_id: str, documents: List[EmbeddingDocument]) -> EmbeddingResult:
        if not documents:
            return EmbeddingResult(inserted_count=0, updated_count=0, deleted_count=0)

        ids = []
        texts = []
        metadatas = []
        embeddings = []

        for doc in documents:
            # Flatten ChunkMetadata to conform to ChromaDB's simple JSON values constraint
            meta_dict = {
                "repository_id": doc.repository_id,
                "file_path": doc.file_path,
                "module_name": doc.module_name,
                "entity_name": doc.entity_name,
                "entity_type": doc.entity_type,
                "language": doc.language,
                "resource_uri": doc.resource_uri,
                # Serialized array values
                "symbols": json.dumps(doc.metadata.symbols),
                "dependencies": json.dumps(doc.metadata.dependencies),
                "complexity_score": doc.metadata.complexity_score,
                "relative_path": doc.metadata.relative_path,
                "package_name": doc.metadata.package_name,
                "start_line": doc.metadata.start_line,
                "end_line": doc.metadata.end_line,
                "repository_name": doc.metadata.repository_name,
                "branch": doc.metadata.branch,
                "parser_version": doc.metadata.parser_version,
                "indexed_at": doc.metadata.indexed_at,
            }
            
            ids.append(doc.id)
            texts.append(doc.text)
            metadatas.append(meta_dict)
            
            # If doc already has pre-computed embedding use it, otherwise call provider
            vector = doc.embedding or self.provider.embed_text(doc.text)
            embeddings.append(vector)

        logger.info(f"Upserting {len(documents)} chunks to ChromaDB collection for repo: {repository_id}")
        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings
        )

        return EmbeddingResult(
            inserted_count=len(documents),
            updated_count=0,
            deleted_count=0
        )

    def delete_repository(self, repository_id: str) -> None:
        logger.info(f"Deleting vector index records for repository: {repository_id}")
        self.collection.delete(where={"repository_id": repository_id})

    def delete_file_documents(self, repository_id: str, relative_path: str) -> None:
        logger.info(f"Deleting vector index chunks for file: {relative_path} in repo: {repository_id}")
        self.collection.delete(
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"relative_path": relative_path}
                ]
            }
        )

    def search(self, repository_id: str, branch: str, query_vector: List[float], top_k: int) -> List[SearchResult]:
        logger.info(f"Performing similarity search for query vector in repo: {repository_id}")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"branch": branch}
                ]
            }
        )
        return self._format_query_results(results)

    def search_by_file(self, repository_id: str, branch: str, file_path: str, top_k: int) -> List[SearchResult]:
        # Embed the file path metadata constraint
        query_vector = self.provider.embed_text(f"file path: {file_path}")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"branch": branch},
                    {"relative_path": file_path}
                ]
            }
        )
        return self._format_query_results(results)

    def search_by_symbol(self, repository_id: str, branch: str, symbol: str, top_k: int) -> List[SearchResult]:
        query_vector = self.provider.embed_text(f"code symbol definition: {symbol}")
        # Search all records matching the symbol query
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"branch": branch}
                ]
            }
        )
        # Filter matching symbol in-memory to ensure correctness
        all_results = self._format_query_results(results)
        matched = []
        for r in all_results:
            if symbol in r.document.metadata.symbols or r.document.entity_name == symbol:
                matched.append(r)
        return matched[:top_k] if matched else all_results[:top_k]

    def search_by_dependency(self, repository_id: str, branch: str, dependency: str, top_k: int) -> List[SearchResult]:
        query_vector = self.provider.embed_text(f"import dependency library: {dependency}")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"branch": branch}
                ]
            }
        )
        all_results = self._format_query_results(results)
        matched = []
        for r in all_results:
            if dependency in r.document.metadata.dependencies:
                matched.append(r)
        return matched[:top_k] if matched else all_results[:top_k]

    def search_by_language(self, repository_id: str, branch: str, language: str, top_k: int) -> List[SearchResult]:
        query_vector = self.provider.embed_text(f"code language: {language}")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={
                "$and": [
                    {"repository_id": repository_id},
                    {"branch": branch},
                    {"language": language}
                ]
            }
        )
        return self._format_query_results(results)

    def repository_statistics(self, repository_id: str) -> KnowledgeBaseStats:
        logger.info(f"Gathering metrics for repository: {repository_id}")
        data = self.collection.get(
            where={"repository_id": repository_id},
            include=["metadatas", "documents"]
        )

        metadatas = data.get("metadatas") or []
        documents = data.get("documents") or []

        indexed_chunks = len(metadatas)
        unique_files = set()
        last_indexed = "unknown"
        total_chars = 0

        for idx, meta in enumerate(metadatas):
            unique_files.add(meta.get("relative_path", ""))
            last_indexed = max(last_indexed, meta.get("indexed_at", ""))
            if idx < len(documents):
                total_chars += len(documents[idx])

        avg_chunk_size = total_chars / indexed_chunks if indexed_chunks > 0 else 0.0
        # Estimate storage size (char length + typical metadata overhead)
        storage_size = total_chars + (indexed_chunks * 256)

        return KnowledgeBaseStats(
            indexed_files=len(unique_files),
            indexed_chunks=indexed_chunks,
            embedding_model=settings.EMBEDDING_MODEL,
            last_indexed_at=last_indexed if last_indexed != "unknown" else datetime.now(timezone.utc).isoformat(),
            average_chunk_size=avg_chunk_size,
            storage_size=storage_size
        )

    def _format_query_results(self, query_results: Dict[str, Any]) -> List[SearchResult]:
        """Formatting helper mapping raw ChromaDB dictionaries to domain SearchResult models."""
        formatted = []
        
        ids = query_results.get("ids", [[]])[0]
        documents = query_results.get("documents", [[]])[0]
        metadatas = query_results.get("metadatas", [[]])[0]
        distances = query_results.get("distances", [[]])[0]

        for i in range(len(ids)):
            meta = metadatas[i]
            
            # De-serialize arrays
            try:
                symbols = json.loads(meta.get("symbols", "[]"))
            except Exception:
                symbols = []
            try:
                dependencies = json.loads(meta.get("dependencies", "[]"))
            except Exception:
                dependencies = []

            chunk_metadata = ChunkMetadata(
                symbols=symbols,
                dependencies=dependencies,
                complexity_score=int(meta.get("complexity_score", 0)),
                relative_path=meta.get("relative_path", ""),
                package_name=meta.get("package_name", ""),
                start_line=int(meta.get("start_line", 0)),
                end_line=int(meta.get("end_line", 0)),
                repository_name=meta.get("repository_name", ""),
                branch=meta.get("branch", ""),
                language=meta.get("language", ""),
                entity_type=meta.get("entity_type", ""),
                parser_version=meta.get("parser_version", ""),
                indexed_at=meta.get("indexed_at", ""),
            )

            doc = EmbeddingDocument(
                id=ids[i],
                repository_id=meta.get("repository_id", ""),
                file_path=meta.get("file_path", ""),
                module_name=meta.get("module_name", ""),
                entity_name=meta.get("entity_name", ""),
                entity_type=meta.get("entity_type", ""),
                language=meta.get("language", ""),
                text=documents[i],
                metadata=chunk_metadata,
                resource_uri=meta.get("resource_uri", ""),
            )

            # Cosine similarity score is derived from cosine distance (similarity = 1 - distance)
            distance = distances[i] if i < len(distances) else 0.0
            score = 1.0 - distance

            formatted.append(
                SearchResult(
                    document=doc,
                    score=score,
                    distance=distance,
                    matched_metadata=meta
                )
            )

        return formatted
