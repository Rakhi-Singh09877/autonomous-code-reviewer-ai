import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.config import settings
from app.core.logging import logger
from app.domain.models.parser import CodebaseStructure, ParsedFile
from app.domain.models.embedding import EmbeddingResult
from app.use_cases.interfaces.embedding_port import EmbeddingPort
from app.infrastructure.rag.embedding_generator import EmbeddingGenerator

class HashRegistry:
    """
    Local repository-level hash registry to enable incremental indexing.
    """
    def __init__(self, persist_dir: Path):
        self.registry_dir = Path(persist_dir) / "hash_registry"
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, repository_id: str) -> Path:
        return self.registry_dir / f"{repository_id}.json"

    def load(self, repository_id: str) -> Dict[str, str]:
        path = self._get_path(repository_id)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read hash registry for {repository_id}: {e}")
        return {}

    def save(self, repository_id: str, registry: Dict[str, str]) -> None:
        path = self._get_path(repository_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hash registry for {repository_id}: {e}")

    def delete(self, repository_id: str) -> None:
        path = self._get_path(repository_id)
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass

class EmbeddingService:
    """
    Service coordinating incremental embedding generation and database indexing.
    """
    def __init__(self, vector_store: EmbeddingPort):
        self.store = vector_store
        self.generator = EmbeddingGenerator()
        self.registry = HashRegistry(Path(settings.CHROMA_PERSIST_DIR))

    def index_repository(
        self,
        repository_id: str,
        repository_name: str,
        branch: str,
        codebase: CodebaseStructure
    ) -> Tuple[EmbeddingResult, str]:
        """
        Processes codebase, checks file hashes, indexes changes in vector store,
        and computes a unique repository fingerprint.
        """
        logger.info(f"Beginning incremental vector indexing for repo: {repository_id}")
        
        # Load existing file hashes
        existing_hashes = self.registry.load(repository_id)
        new_hashes: Dict[str, str] = {}
        
        inserted = 0
        deleted = 0
        updated = 0
        failed: List[str] = []

        files_hashes_list: List[Tuple[str, str]] = []

        for parsed_file in codebase.files:
            rel_path = parsed_file.relative_path
            
            # Compute file hash based on symbols, dependencies and lines
            content_sig = f"{parsed_file.line_count}:{parsed_file.char_count}:{parsed_file.symbols}:{parsed_file.dependencies}"
            file_hash = hashlib.md5(content_sig.encode("utf-8")).hexdigest()
            files_hashes_list.append((rel_path, file_hash))
            new_hashes[rel_path] = file_hash

            # Check if file has changed
            old_hash = existing_hashes.get(rel_path)
            if old_hash == file_hash:
                logger.info(f"Skipping index update (unchanged): {rel_path}")
                continue

            try:
                # Delete existing documents for the file (if updating)
                if old_hash is not None:
                    self.store.delete_file_documents(repository_id, rel_path)
                    deleted += len(parsed_file.chunks)
                    updated += 1
                else:
                    inserted += 1

                # Generate new documents and upsert
                docs = self.generator.generate_documents(
                    repository_id=repository_id,
                    repository_name=repository_name,
                    branch=branch,
                    parsed_file=parsed_file
                )
                self.store.upsert_documents(repository_id, docs)
            except Exception as e:
                logger.error(f"Failed to index file {rel_path}: {e}")
                failed.append(rel_path)

        # Handle deleted files (files in existing registry but not in current codebase)
        for rel_path in list(existing_hashes.keys()):
            if rel_path not in new_hashes:
                logger.info(f"Purging deleted file from index: {rel_path}")
                try:
                    self.store.delete_file_documents(repository_id, rel_path)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete index for {rel_path}: {e}")

        # Save the updated hashes mapping
        self.registry.save(repository_id, new_hashes)

        # Compute a unique repository fingerprint
        fingerprint = self.compute_repository_fingerprint(files_hashes_list)

        result = EmbeddingResult(
            inserted_count=inserted,
            updated_count=updated,
            deleted_count=deleted,
            failed_files=failed
        )
        return result, fingerprint

    def purge_repository(self, repository_id: str) -> None:
        """Removes all indexed chunks and registry cache for the repository."""
        self.store.delete_repository(repository_id)
        self.registry.delete(repository_id)

    def compute_repository_fingerprint(self, files_with_hashes: List[Tuple[str, str]]) -> str:
        """
        Computes a stable SHA-256 fingerprint representing the files configuration.
        """
        sorted_files = sorted(files_with_hashes, key=lambda x: x[0])
        hasher = hashlib.sha256()
        for rel_path, fhash in sorted_files:
            hasher.update(f"{rel_path}:{fhash}".encode("utf-8"))
        return hasher.hexdigest()
