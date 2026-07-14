import json
import shutil
import tempfile
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.models.parser import ParsedFile
from app.domain.models.embedding import ChunkMetadata, EmbeddingDocument
from app.infrastructure.rag.embedding_provider import OpenAIEmbeddingProvider
from app.infrastructure.rag.chroma_store import ChromaVectorStore
from app.infrastructure.rag.embedding_generator import EmbeddingGenerator
from app.infrastructure.rag.embedding_service import EmbeddingService

@pytest.fixture
def temp_chroma_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_embedding_provider():
    provider = OpenAIEmbeddingProvider(api_key="", dimensions=1536)
    vector = provider.embed_text("test code segment")
    assert len(vector) == 1536
    # Unit length check (L2 norm should be approximately 1.0)
    sq_sum = sum(x * x for x in vector)
    assert pytest.approx(sq_sum, abs=1e-5) == 1.0

def test_embedding_generator():
    generator = EmbeddingGenerator()
    
    # Create mock ParsedFile
    parsed = ParsedFile(
        file_path=Path("/workspace/main.py"),
        relative_path="main.py",
        module_name="main",
        package_name="",
        language="Python",
        imports=["os"],
        classes=[],
        functions=[],
        todos=[],
        line_count=10,
        char_count=100,
        parse_status="success",
        symbols=["MathOps"],
        dependencies=["os"],
        complexity_score=2,
        has_tests=False,
        chunks=[
            {
                "id": "main.py#overview",
                "entity_name": "module_overview",
                "text": "File main.py overview",
                "metadata": {"type": "overview"}
            },
            {
                "id": "main.py#func-add",
                "entity_name": "add",
                "text": "def add(a, b): return a + b",
                "metadata": {"type": "function", "start_line": 5, "end_line": 7}
            }
        ]
    )

    docs = generator.generate_documents(
        repository_id="repo-123",
        repository_name="test-repo",
        branch="main",
        parsed_file=parsed
    )

    assert len(docs) == 2
    assert docs[0].id == "main.py#overview"
    assert docs[0].repository_id == "repo-123"
    assert docs[0].resource_uri == "mcp://repo-123/main.py"
    
    assert docs[1].id == "main.py#func-add"
    assert docs[1].resource_uri == "mcp://repo-123/main.py#L5-L7"
    assert docs[1].metadata.start_line == 5
    assert docs[1].metadata.end_line == 7
    assert docs[1].metadata.language == "Python"
    assert "MathOps" in docs[1].metadata.symbols

def test_chroma_vector_store_operations(temp_chroma_dir):
    # Set config override locally for persist dir
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.config.settings.CHROMA_PERSIST_DIR", temp_chroma_dir)
        
        provider = OpenAIEmbeddingProvider(api_key="", dimensions=128)
        store = ChromaVectorStore(embedding_provider=provider, persist_dir=temp_chroma_dir)

        # Create mock document
        meta = ChunkMetadata(
            symbols=["calculate"],
            dependencies=["math"],
            complexity_score=1,
            relative_path="math_utils.py",
            package_name="",
            start_line=1,
            end_line=10,
            repository_name="test-repo",
            branch="main",
            language="Python",
            entity_type="function",
            parser_version="1.0.0",
            indexed_at="2026-07-14T12:00:00Z"
        )
        
        doc = EmbeddingDocument(
            id="math_utils.py#func-calculate",
            repository_id="repo-999",
            file_path="/workspace/math_utils.py",
            module_name="math_utils",
            entity_name="calculate",
            entity_type="function",
            language="Python",
            text="def calculate(x): return x * 2",
            metadata=meta,
            resource_uri="mcp://repo-999/math_utils.py#L1-L10"
        )

        # Upsert
        res = store.upsert_documents("repo-999", [doc])
        assert res.inserted_count == 1

        # Search by symbol
        results = store.search_by_symbol("repo-999", "main", "calculate", top_k=1)
        assert len(results) == 1
        assert results[0].document.entity_name == "calculate"
        assert results[0].score > 0.0

        # Search by file
        results = store.search_by_file("repo-999", "main", "math_utils.py", top_k=1)
        assert len(results) == 1
        assert results[0].document.metadata.relative_path == "math_utils.py"

        # Search by dependency
        results = store.search_by_dependency("repo-999", "main", "math", top_k=1)
        assert len(results) == 1
        assert "math" in results[0].document.metadata.dependencies

        # Stats
        stats = store.repository_statistics("repo-999")
        assert stats.indexed_files == 1
        assert stats.indexed_chunks == 1

        # Clean
        store.delete_repository("repo-999")
        stats_empty = store.repository_statistics("repo-999")
        assert stats_empty.indexed_chunks == 0

def test_embedding_service_incremental(temp_chroma_dir):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.core.config.settings.CHROMA_PERSIST_DIR", temp_chroma_dir)
        
        provider = OpenAIEmbeddingProvider(api_key="", dimensions=128)
        store = ChromaVectorStore(embedding_provider=provider, persist_dir=temp_chroma_dir)
        service = EmbeddingService(vector_store=store)

        parsed1 = ParsedFile(
            file_path=Path("/workspace/a.py"),
            relative_path="a.py",
            module_name="a",
            package_name="",
            language="Python",
            imports=[],
            classes=[],
            functions=[],
            todos=[],
            line_count=5,
            char_count=50,
            parse_status="success",
            symbols=["foo"],
            dependencies=[],
            complexity_score=1,
            has_tests=False,
            chunks=[{
                "id": "a.py#func-foo",
                "entity_name": "foo",
                "text": "def foo(): pass",
                "metadata": {"type": "function"}
            }]
        )

        from app.domain.models.parser import CodebaseStructure
        codebase = CodebaseStructure(
            files=[parsed1],
            total_files=1,
            parsed_files=1,
            failed_files=0,
            unsupported_files=0,
            language_statistics={"Python": 1}
        )

        # First indexing pass
        res1, fingerprint1 = service.index_repository("repo-hash-1", "test-repo", "main", codebase)
        assert res1.inserted_count == 1
        assert res1.updated_count == 0
        assert len(fingerprint1) == 64

        # Second pass with no changes (should skip indexing)
        res2, fingerprint2 = service.index_repository("repo-hash-1", "test-repo", "main", codebase)
        assert res2.inserted_count == 0
        assert res2.updated_count == 0
        assert fingerprint2 == fingerprint1

        # Third pass with modified file
        parsed1_modified = ParsedFile(
            file_path=Path("/workspace/a.py"),
            relative_path="a.py",
            module_name="a",
            package_name="",
            language="Python",
            imports=[],
            classes=[],
            functions=[],
            todos=[],
            line_count=6,
            char_count=60,
            parse_status="success",
            symbols=["foo", "bar"], # change symbols to trigger hash change
            dependencies=[],
            complexity_score=1,
            has_tests=False,
            chunks=[{
                "id": "a.py#func-foo",
                "entity_name": "foo",
                "text": "def foo(): pass",
                "metadata": {"type": "function"}
            }]
        )
        codebase_mod = CodebaseStructure(
            files=[parsed1_modified],
            total_files=1,
            parsed_files=1,
            failed_files=0,
            unsupported_files=0,
            language_statistics={"Python": 1}
        )
        res3, fingerprint3 = service.index_repository("repo-hash-1", "test-repo", "main", codebase_mod)
        assert res3.updated_count == 1
        assert fingerprint3 != fingerprint1

        # Purge
        service.purge_repository("repo-hash-1")
        stats = store.repository_statistics("repo-hash-1")
        assert stats.indexed_chunks == 0
