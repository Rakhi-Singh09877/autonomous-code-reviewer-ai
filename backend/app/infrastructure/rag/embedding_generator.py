from datetime import datetime, timezone
from typing import List
from app.domain.models.parser import ParsedFile
from app.domain.models.embedding import EmbeddingDocument, ChunkMetadata

class EmbeddingGenerator:
    """
    Infrastructure class to convert ParsedFile objects to RAG-ready EmbeddingDocument entities.
    """

    def generate_documents(
        self,
        repository_id: str,
        repository_name: str,
        branch: str,
        parsed_file: ParsedFile,
        parser_version: str = "1.0.0"
    ) -> List[EmbeddingDocument]:
        documents = []
        indexed_at = datetime.now(timezone.utc).isoformat()

        # Build documents from individual chunks defined inside parsed_file
        for chunk in parsed_file.chunks:
            # Map ChunkMetadata
            chunk_metadata = ChunkMetadata(
                symbols=parsed_file.symbols,
                dependencies=parsed_file.dependencies,
                complexity_score=parsed_file.complexity_score,
                relative_path=parsed_file.relative_path,
                package_name=parsed_file.package_name,
                start_line=chunk["metadata"].get("start_line", 0),
                end_line=chunk["metadata"].get("end_line", 0),
                repository_name=repository_name,
                branch=branch,
                language=parsed_file.language,
                entity_type=chunk["metadata"].get("type", "unknown"),
                parser_version=parser_version,
                indexed_at=indexed_at,
            )

            # Establish resource URI compatible with Model Context Protocol (MCP)
            resource_uri = f"mcp://{repository_id}/{parsed_file.relative_path}"
            if "start_line" in chunk["metadata"]:
                resource_uri += f"#L{chunk['metadata']['start_line']}-L{chunk['metadata']['end_line']}"

            doc = EmbeddingDocument(
                id=chunk["id"],
                repository_id=repository_id,
                file_path=str(parsed_file.file_path),
                module_name=parsed_file.module_name,
                entity_name=chunk["entity_name"],
                entity_type=chunk["metadata"].get("type", "unknown"),
                language=parsed_file.language,
                text=chunk["text"],
                metadata=chunk_metadata,
                resource_uri=resource_uri,
            )
            documents.append(doc)

        return documents
