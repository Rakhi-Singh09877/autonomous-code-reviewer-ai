import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.domain.models.analysis import ReviewPolicy, PromptVersion
from app.domain.models.issue import ReviewIssueSeverity, ReviewIssueCategory
from app.domain.models.parser import ParsedFile
from app.domain.models.report import TokenUsageMetadata
from app.use_cases.interfaces.llm_port import LLMPort
from app.infrastructure.agents.review_agent import ReviewAgent

@pytest.fixture
def temp_code_file():
    temp_dir = tempfile.mkdtemp()
    file_path = Path(temp_dir) / "sample.py"
    content = "def calculate(a, b):\n    return a + b\n\n# Todo: test it\n"
    file_path.write_text(content, encoding="utf-8")
    yield file_path
    try:
        file_path.unlink()
        Path(temp_dir).rmdir()
    except Exception:
        pass

@pytest.mark.asyncio
async def test_review_agent_basic(temp_code_file):
    # Setup Mock LLM Port
    mock_llm = MagicMock(spec=LLMPort)
    
    # Mock LLM returned structured issues
    mock_issues = {
        "issues": [
            {
                "line_start": 4,
                "line_end": 4,
                "category": "BEST_PRACTICES",
                "severity": "LOW",
                "confidence": 0.9,
                "description": "Found todo",
                "explanation": "TODO notes left.",
                "suggested_fix": "Implement tests.",
                "snippet": "# Todo: test it"
            }
        ]
    }
    mock_usage = TokenUsageMetadata(100, 50, 150, 0.001)
    
    mock_llm.generate_structured_output = AsyncMock(return_value=(mock_issues, mock_usage))
    
    agent = ReviewAgent(mock_llm)
    
    # Configure parsed file
    parsed_file = ParsedFile(
        file_path=temp_code_file,
        relative_path="sample.py",
        module_name="sample",
        package_name="",
        language="Python",
        imports=[],
        classes=[],
        functions=[],
        todos=[],
        line_count=4,
        char_count=50,
        parse_status="success",
        symbols=[],
        dependencies=[],
        complexity_score=1,
        has_tests=False
    )
    
    policy = ReviewPolicy(
        rules=[],
        custom_instructions=None,
        focus_areas=[],
        max_issues_per_file=5
    )
    
    result = await agent.analyze_file(
        file_path=temp_code_file,
        parsed_file=parsed_file,
        repo_context="test context",
        rag_chunks=[],
        policy=policy
    )
    
    assert result.file_path == temp_code_file
    assert len(result.issues) == 1
    assert result.issues[0].line_start == 4
    assert result.issues[0].category == ReviewIssueCategory.BEST_PRACTICES
    assert result.issues[0].severity == ReviewIssueSeverity.LOW
    
    # Score calculations: initial 100 - LOW deduction (2) = 98
    assert result.score == 98
    assert result.token_usage.total_tokens == 150
    assert result.token_usage.estimated_cost_usd == 0.001

@pytest.mark.asyncio
async def test_review_agent_line_clipping(temp_code_file):
    mock_llm = MagicMock(spec=LLMPort)
    
    # Mock issue with out-of-bounds line numbers (e.g. line 999 in a 4-line file)
    mock_issues = {
        "issues": [
            {
                "line_start": 999,
                "line_end": 1000,
                "category": "CODE_SMELLS",
                "severity": "CRITICAL",
                "confidence": 0.8,
                "description": "Out of bounds issue",
                "explanation": "Out of bounds.",
                "suggested_fix": "Fix lines.",
                "snippet": "bad line"
            }
        ]
    }
    mock_usage = TokenUsageMetadata(50, 20, 70, 0.0)
    mock_llm.generate_structured_output = AsyncMock(return_value=(mock_issues, mock_usage))
    
    agent = ReviewAgent(mock_llm)
    
    parsed_file = ParsedFile(
        file_path=temp_code_file,
        relative_path="sample.py",
        module_name="sample",
        package_name="",
        language="Python",
        imports=[],
        classes=[],
        functions=[],
        todos=[],
        line_count=4,  # actual file is 4 lines
        char_count=50,
        parse_status="success",
        symbols=[],
        dependencies=[],
        complexity_score=1,
        has_tests=False
    )
    
    result = await agent.analyze_file(
        file_path=temp_code_file,
        parsed_file=parsed_file,
        repo_context="test",
        rag_chunks=[],
        policy=ReviewPolicy()
    )
    
    assert len(result.issues) == 1
    # Line start and line end should clip to file maximum (4)
    assert result.issues[0].line_start == 4
    assert result.issues[0].line_end == 4
    
    # Deduction: CRITICAL is -25 -> Score should be 75
    assert result.score == 75

@pytest.mark.asyncio
async def test_review_agent_chunking(temp_code_file):
    mock_llm = MagicMock(spec=LLMPort)
    
    # Mock calls for chunk reviews
    mock_issues_chunk = {"issues": []}
    mock_usage = TokenUsageMetadata(100, 50, 150, 0.001)
    mock_llm.generate_structured_output = AsyncMock(return_value=(mock_issues_chunk, mock_usage))
    
    agent = ReviewAgent(mock_llm)
    
    parsed_file = MagicMock(spec=ParsedFile)
    parsed_file.file_path = temp_code_file
    parsed_file.relative_path = Path("sample.py")
    parsed_file.language = "Python"
    parsed_file.complexity_score = 1
    parsed_file.has_tests = False
    
    policy = ReviewPolicy()
    
    # Mock config window limit to be very small, forcing chunking
    with patch.object(settings, "REVIEW_CONTEXT_WINDOW_LIMIT", 5):
        result = await agent.analyze_file(
            file_path=temp_code_file,
            parsed_file=parsed_file,
            repo_context="test",
            rag_chunks=[],
            policy=policy
        )
        
        # Verify that chunking was executed (generate_structured_output called on segments)
        assert mock_llm.generate_structured_output.called
        # Token usage sums up
        assert result.token_usage.total_tokens > 0

@pytest.mark.asyncio
async def test_review_agent_policy_issue_limits(temp_code_file):
    mock_llm = MagicMock(spec=LLMPort)
    
    # Return 3 issues
    mock_issues = {
        "issues": [
            {
                "line_start": 1, "line_end": 1,
                "category": "CODE_QUALITY", "severity": "INFO",
                "confidence": 0.8, "description": "Info issue",
                "explanation": "", "suggested_fix": "", "snippet": ""
            },
            {
                "line_start": 2, "line_end": 2,
                "category": "PERFORMANCE", "severity": "CRITICAL",
                "confidence": 0.8, "description": "Perf issue",
                "explanation": "", "suggested_fix": "", "snippet": ""
            },
            {
                "line_start": 3, "line_end": 3,
                "category": "SECURITY", "severity": "HIGH",
                "confidence": 0.8, "description": "Sec issue",
                "explanation": "", "suggested_fix": "", "snippet": ""
            }
        ]
    }
    
    mock_llm.generate_structured_output = AsyncMock(return_value=(mock_issues, TokenUsageMetadata()))
    agent = ReviewAgent(mock_llm)
    
    parsed_file = ParsedFile(
        file_path=temp_code_file,
        relative_path="sample.py",
        module_name="sample",
        package_name="",
        language="Python",
        imports=[],
        classes=[],
        functions=[],
        todos=[],
        line_count=4,
        char_count=50,
        parse_status="success",
        symbols=[],
        dependencies=[],
        complexity_score=1,
        has_tests=False
    )
    
    # Limit to max 2 issues
    policy = ReviewPolicy(max_issues_per_file=2)
    
    result = await agent.analyze_file(
        file_path=temp_code_file,
        parsed_file=parsed_file,
        repo_context="test",
        rag_chunks=[],
        policy=policy
    )
    
    # Issues should be capped at 2
    assert len(result.issues) == 2
    # The capped issues should be the ones with highest severity (CRITICAL and HIGH, not INFO)
    severities = [issue.severity for issue in result.issues]
    assert ReviewIssueSeverity.CRITICAL in severities
    assert ReviewIssueSeverity.HIGH in severities
    assert ReviewIssueSeverity.INFO not in severities
