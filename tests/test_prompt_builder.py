import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.models.analysis import ReviewPolicy, PromptVersion
from app.domain.models.embedding import EmbeddingDocument, ChunkMetadata, SearchResult
from app.infrastructure.llm.prompts.builder import PromptBuilder

def test_prompt_builder_basic():
    policy = ReviewPolicy(
        rules=["Do not use bare except clauses", "Keep functions under 50 lines"],
        custom_instructions="Focus on clean architecture.",
        focus_areas=["security", "performance"],
        prompt_version=PromptVersion.REVIEW_V1
    )
    
    file_content = "def test_func():\n    try:\n        do_something()\n    except:\n        pass"
    repo_metadata = {"name": "test_repo", "version": "1.0"}
    
    # Mock RAG Chunk
    metadata = ChunkMetadata(
        symbols=["do_something"],
        dependencies=[],
        complexity_score=1,
        relative_path="lib.py",
        package_name="lib",
        start_line=1,
        end_line=5,
        repository_name="test_repo",
        branch="main",
        language="Python",
        entity_type="function",
        parser_version="1",
        indexed_at="2026-07-14T00:00:00Z"
    )
    doc = EmbeddingDocument(
        id="chunk_1",
        repository_id="repo_123",
        file_path="lib.py",
        module_name="lib",
        entity_name="do_something",
        entity_type="function",
        language="Python",
        text="def do_something():\n    print('done')",
        metadata=metadata,
        resource_uri="mcp://repositories/repo_123/chunks/chunk_1"
    )
    rag_chunks = [SearchResult(document=doc, score=0.9, distance=0.1, matched_metadata={})]

    system_prompt, user_prompt = PromptBuilder.build_prompts(
        file_path="app.py",
        language="Python",
        repo_metadata=repo_metadata,
        policy=policy,
        rag_chunks=rag_chunks,
        file_content=file_content
    )

    # Assertions
    assert "You are an elite, senior software developer" in system_prompt
    assert "File Path: app.py" in user_prompt
    assert "Programming Language: Python" in user_prompt
    assert "name=test_repo" in user_prompt
    assert "Do not use bare except clauses" in user_prompt
    assert "Focus on clean architecture." in user_prompt
    assert '<rag_context id="chunk_1"' in user_prompt
    assert "1: def test_func():" in user_prompt
    assert "5:         pass" in user_prompt

def test_prompt_builder_line_offset():
    policy = ReviewPolicy(prompt_version=PromptVersion.REVIEW_V1)
    file_content = "lineA\nlineB"
    
    _, user_prompt = PromptBuilder.build_prompts(
        file_path="test.py",
        language="Python",
        repo_metadata={},
        policy=policy,
        rag_chunks=[],
        file_content=file_content,
        line_offset=10
    )
    
    assert "11: lineA" in user_prompt
    assert "12: lineB" in user_prompt

def test_prompt_builder_versions():
    # Security version
    policy = ReviewPolicy(prompt_version=PromptVersion.SECURITY_V1)
    system_prompt, user_prompt = PromptBuilder.build_prompts(
        file_path="test.py",
        language="Python",
        repo_metadata={},
        policy=policy,
        rag_chunks=[],
        file_content="pass"
    )
    assert "cybersecurity auditor" in system_prompt
    assert "--- Security Policy ---" in user_prompt
