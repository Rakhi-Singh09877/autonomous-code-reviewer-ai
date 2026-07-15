import io
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import uuid
from datetime import datetime, timezone

from app.domain.models.repository import Repository, RepositorySourceType
from app.domain.models.language import LanguageDetectionResult
from app.domain.models.parser import ParsedFile, CodebaseStructure
from app.domain.models.embedding import SearchResult, EmbeddingDocument, ChunkMetadata, EmbeddingResult
from app.domain.models.analysis import ReviewPolicy
from app.domain.models.report import FileReviewResult, TokenUsageMetadata, RepositoryReviewReport
from app.domain.models.issue import ReviewIssue, ReviewIssueSeverity, ReviewIssueCategory

from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.use_cases.interfaces.detector_port import LanguageDetectorPort
from app.use_cases.interfaces.parser_port import CodeParserPort
from app.use_cases.interfaces.embedding_port import EmbeddingPort, EmbeddingProvider
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.agent_ports import ReviewAgentPort
from app.use_cases.interfaces.report_port import ReportPort

from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator
from app.infrastructure.rag.rag_engine import RAGEngine
from app.infrastructure.report.generator import MarkdownReportGenerator

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)

@pytest.fixture
def mock_ports():
    return {
        "loader": MagicMock(spec=RepositoryLoaderPort),
        "detector": MagicMock(spec=LanguageDetectorPort),
        "parser": MagicMock(spec=CodeParserPort),
        "embedding": MagicMock(spec=EmbeddingPort),
        "rag": MagicMock(spec=RAGPort),
        "review_agent": MagicMock(spec=ReviewAgentPort),
        "report": MagicMock(spec=ReportPort)
    }

@pytest.mark.asyncio
async def test_orchestrator_success_flow(temp_dir, mock_ports):
    # Setup mock workspace files
    file1 = temp_dir / "main.py"
    file1.write_text("def main(): pass", encoding="utf-8")
    
    # 1. Loader mock
    repo_id = uuid.uuid4()
    mock_repo = Repository(
        local_path=temp_dir,
        source_type=RepositorySourceType.GIT,
        file_count=1,
        total_size_bytes=100,
        id=repo_id,
        branch="main",
        git_url="https://github.com/test/repo"
    )
    mock_ports["loader"].load_from_git.return_value = mock_repo
    
    # 2. Detector mock
    mock_ports["detector"].detect_file_language.return_value = LanguageDetectionResult(
        file_path=file1,
        language="Python",
        confidence=1.0,
        detection_method="extension",
        extension=".py",
        encoding="utf-8",
        file_size=16,
        is_binary=False
    )
    
    # 3. Parser mock
    mock_parsed_file = ParsedFile(
        file_path=file1,
        relative_path="main.py",
        module_name="main",
        package_name="",
        language="Python",
        imports=[],
        classes=[],
        functions=[],
        todos=[],
        line_count=1,
        char_count=16,
        parse_status="success",
        symbols=["main"],
        dependencies=[],
        complexity_score=1,
        has_tests=False,
        chunks=[{
            "id": "main.py#func-main",
            "entity_name": "main",
            "text": "def main(): pass",
            "metadata": {"type": "function", "start_line": 1, "end_line": 1}
        }]
    )
    mock_ports["parser"].parse_repository.return_value = CodebaseStructure(
        files=[mock_parsed_file],
        total_files=1,
        parsed_files=1,
        failed_files=0,
        unsupported_files=0,
        language_statistics={"Python": 1}
    )
    
    # 4. Embedding mock
    mock_ports["embedding"].upsert_documents.return_value = EmbeddingResult(1, 0, 0)
    
    # 5. RAG mock
    mock_metadata = ChunkMetadata(
        symbols=["main"],
        dependencies=[],
        complexity_score=1,
        relative_path="main.py",
        package_name="",
        start_line=1,
        end_line=1,
        repository_name="temp_dir",
        branch="main",
        language="Python",
        entity_type="function",
        parser_version="1.0.0",
        indexed_at="2026-07-14T12:00:00Z"
    )
    mock_doc = EmbeddingDocument(
        id="main.py#func-main",
        repository_id=str(repo_id),
        file_path=str(file1),
        module_name="main",
        entity_name="main",
        entity_type="function",
        language="Python",
        text="def main(): pass",
        metadata=mock_metadata,
        resource_uri="mcp://main.py"
    )
    mock_ports["rag"].retrieve_context_chunks = AsyncMock(return_value=[
        SearchResult(document=mock_doc, score=0.9, distance=0.1, matched_metadata={})
    ])
    
    # 6. Review Agent mock
    mock_issue = ReviewIssue(
        id=uuid.uuid4(),
        file_path=file1,
        line_start=1,
        line_end=1,
        category=ReviewIssueCategory.BEST_PRACTICES,
        severity=ReviewIssueSeverity.LOW,
        confidence=0.9,
        description="Missing docstring",
        explanation="Functions should have docstrings.",
        suggested_fix="def main():\n    \"\"\"Docstring\"\"\"\n    pass",
        snippet="def main(): pass"
    )
    mock_ports["review_agent"].analyze_file = AsyncMock(return_value=FileReviewResult(
        file_path=file1,
        issues=[mock_issue],
        score=98,
        review_time_sec=1.5,
        token_usage=TokenUsageMetadata(50, 20, 70, 0.0001)
    ))
    
    # 7. Report mock
    mock_ports["report"].generate_report.return_value = "# Report"

    orchestrator = RepositoryAnalysisOrchestrator(
        loader_port=mock_ports["loader"],
        detector_port=mock_ports["detector"],
        parser_port=mock_ports["parser"],
        embedding_port=mock_ports["embedding"],
        rag_port=mock_ports["rag"],
        review_agent_port=mock_ports["review_agent"],
        report_port=mock_ports["report"]
    )
    
    report = await orchestrator.analyze_repository(git_url="https://github.com/test/repo", branch="main")
    
    assert isinstance(report, RepositoryReviewReport)
    assert report.repository_id == repo_id
    assert report.files_reviewed == 1
    assert report.total_issues == 1
    assert report.average_score == 98.0
    assert report.token_usage.total_tokens == 70
    assert report.token_usage.estimated_cost_usd == pytest.approx(0.0001)
    assert report.issues_by_severity["LOW"] == 1
    assert report.issues_by_category["BEST_PRACTICES"] == 1
    
    mock_ports["loader"].cleanup.assert_called_once_with(mock_repo)

@pytest.mark.asyncio
async def test_orchestrator_resiliency_on_file_failure(temp_dir, mock_ports):
    # Two files
    file1 = temp_dir / "file1.py"
    file1.write_text("def f1(): pass", encoding="utf-8")
    file2 = temp_dir / "file2.py"
    file2.write_text("def f2(): pass", encoding="utf-8")
    
    repo_id = uuid.uuid4()
    mock_repo = Repository(
        local_path=temp_dir,
        source_type=RepositorySourceType.GIT,
        file_count=2,
        total_size_bytes=200,
        id=repo_id,
        branch="main",
        git_url="https://github.com/test/repo"
    )
    mock_ports["loader"].load_from_git.return_value = mock_repo
    
    # Detector mocks
    mock_ports["detector"].detect_file_language.side_effect = [
        LanguageDetectionResult(file1, "Python", 1.0, "extension", ".py", "utf-8", 14, False),
        LanguageDetectionResult(file2, "Python", 1.0, "extension", ".py", "utf-8", 14, False)
    ]
    
    # Parser mocks
    pf1 = ParsedFile(file1, "file1.py", "file1", "", "Python", [], [], [], [], 1, 14, "success", [], [], 1, False, [])
    pf2 = ParsedFile(file2, "file2.py", "file2", "", "Python", [], [], [], [], 1, 14, "success", [], [], 1, False, [])
    mock_ports["parser"].parse_repository.return_value = CodebaseStructure(
        files=[pf1, pf2],
        total_files=2,
        parsed_files=2,
        failed_files=0,
        unsupported_files=0,
        language_statistics={"Python": 2}
    )
    
    mock_ports["rag"].retrieve_context_chunks = AsyncMock(return_value=[])
    
    # Review Agent mock: file1 succeeds, file2 fails (raises Exception)
    res1 = FileReviewResult(file1, [], 100, 1.0, TokenUsageMetadata(10, 5, 15, 0.0))
    mock_ports["review_agent"].analyze_file.side_effect = [
        res1,
        Exception("LLM failure during file review")
    ]
    
    orchestrator = RepositoryAnalysisOrchestrator(
        loader_port=mock_ports["loader"],
        detector_port=mock_ports["detector"],
        parser_port=mock_ports["parser"],
        embedding_port=mock_ports["embedding"],
        rag_port=mock_ports["rag"],
        review_agent_port=mock_ports["review_agent"],
        report_port=mock_ports["report"]
    )
    
    report = await orchestrator.analyze_repository(git_url="https://github.com/test/repo")
    
    assert report.files_reviewed == 2
    assert len(report.file_results) == 2
    assert report.file_results[0].score == 100
    assert report.file_results[1].score == 100  # Fallback score is 100
    assert report.token_usage.total_tokens == 15  # Only file1 tokens accumulated
    mock_ports["loader"].cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_rag_engine():
    mock_embedding_port = MagicMock(spec=EmbeddingPort)
    mock_provider = MagicMock(spec=EmbeddingProvider)
    
    mock_provider.embed_text.return_value = [0.1, 0.2, 0.3]
    mock_embedding_port.search.return_value = [
        SearchResult(
            document=MagicMock(spec=EmbeddingDocument),
            score=0.95,
            distance=0.05,
            matched_metadata={}
        )
    ]
    
    rag = RAGEngine(vector_store=mock_embedding_port, embedding_provider=mock_provider)
    results = await rag.retrieve_context_chunks("repo-abc", "sample query", limit=3)
    
    mock_provider.embed_text.assert_called_once_with("sample query")
    mock_embedding_port.search.assert_called_once_with(
        repository_id="repo-abc",
        branch="main",
        query_vector=[0.1, 0.2, 0.3],
        top_k=3
    )
    assert len(results) == 1
    assert results[0].score == 0.95

def test_markdown_report_generator(temp_dir):
    generator = MarkdownReportGenerator(output_dir=str(temp_dir))
    
    mock_issue = ReviewIssue(
        id=uuid.uuid4(),
        file_path=Path("utils.py"),
        line_start=5,
        line_end=7,
        category=ReviewIssueCategory.SECURITY,
        severity=ReviewIssueSeverity.CRITICAL,
        confidence=0.99,
        description="SQL Injection",
        explanation="Raw SQL formatted with user input.",
        suggested_fix="Use parameterized queries.",
        snippet="query = f'SELECT * FROM users WHERE id = {user_id}'"
    )
    
    file_result = FileReviewResult(
        file_path=Path("utils.py"),
        issues=[mock_issue],
        score=75,
        review_time_sec=2.45,
        token_usage=TokenUsageMetadata(200, 100, 300, 0.002)
    )
    
    report_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    report = RepositoryReviewReport(
        id=report_id,
        repository_id=repo_id,
        created_at=datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc),
        files_reviewed=1,
        total_issues=1,
        issues_by_severity={"CRITICAL": 1},
        issues_by_category={"SECURITY": 1},
        average_score=75.0,
        file_results=[file_result],
        token_usage=TokenUsageMetadata(200, 100, 300, 0.002)
    )
    
    content = generator.generate_report(report)
    
    assert "Codebase Review Report" in content
    assert str(report_id) in content
    assert "75.0/100" in content
    assert "SQL Injection" in content
    assert "SECURITY" in content
    assert "CRITICAL" in content
    
    report_file = temp_dir / f"report_{report_id}.md"
    assert report_file.exists()
    assert report_file.read_text(encoding="utf-8") == content
