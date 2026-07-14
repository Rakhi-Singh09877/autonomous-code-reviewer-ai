import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.domain.exceptions.agent_exceptions import (
    LLMRateLimitException,
    LLMConnectionException,
    LLMInvalidAPIKeyException,
    LLMResponseParsingException
)
from app.infrastructure.llm.claude import ClaudeLLMAdapter

@pytest.mark.asyncio
async def test_claude_adapter_success():
    # Setup mock
    mock_client = MagicMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 1000
    mock_response.usage.output_tokens = 500
    
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = {
        "issues": [
            {
                "line_start": 5,
                "line_end": 10,
                "category": "BUG_DETECTION",
                "severity": "HIGH",
                "confidence": 0.95,
                "description": "Infinite loop risk",
                "explanation": "Condition check is flawed.",
                "suggested_fix": "break",
                "snippet": "while True:"
            }
        ]
    }
    mock_response.content = [mock_tool_use]
    mock_messages.create.return_value = mock_response
    
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        # Temporarily force API Key
        with patch.object(settings, "ANTHROPIC_API_KEY", "test-api-key"):
            adapter = ClaudeLLMAdapter()
            res, usage = await adapter.generate_structured_output(
                system_prompt="sys",
                user_prompt="user",
                schema={}
            )
            
            # Assertions
            assert "issues" in res
            assert len(res["issues"]) == 1
            assert res["issues"][0]["line_start"] == 5
            
            # Cost calculations assertions
            assert usage.prompt_tokens == 1000
            assert usage.completion_tokens == 500
            assert usage.total_tokens == 1500
            
            # Cost: 1000 * 3 / 1M + 500 * 15 / 1M = 0.003 + 0.0075 = 0.0105
            assert usage.estimated_cost_usd == pytest.approx(0.0105)

@pytest.mark.asyncio
async def test_claude_adapter_rate_limit_retry():
    mock_client = MagicMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    # First request raises RateLimitError, second succeeds
    mock_messages.create.side_effect = [
        anthropic.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body={}
        ),
        MagicMock(
            usage=MagicMock(input_tokens=100, output_tokens=50),
            content=[
                MagicMock(
                    type="tool_use",
                    input={"issues": []}
                )
            ]
        )
    ]
    
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            # Set small retry min wait for fast test execution
            with patch.object(settings, "REVIEW_MAX_RETRIES", 2):
                adapter = ClaudeLLMAdapter()
                res, usage = await adapter.generate_structured_output(
                    system_prompt="sys",
                    user_prompt="user",
                    schema={}
                )
                assert mock_messages.create.call_count == 2
                assert usage.prompt_tokens == 100
                assert "issues" in res

@pytest.mark.asyncio
async def test_claude_adapter_auth_error_no_retry():
    mock_client = MagicMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    # Raises AuthenticationError
    mock_messages.create.side_effect = anthropic.AuthenticationError(
        message="Invalid key",
        response=MagicMock(),
        body={}
    )
    
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with patch.object(settings, "ANTHROPIC_API_KEY", "invalid-key"):
            adapter = ClaudeLLMAdapter()
            with pytest.raises(LLMInvalidAPIKeyException):
                await adapter.generate_structured_output(
                    system_prompt="sys",
                    user_prompt="user",
                    schema={}
                )
            # Assert only 1 call was made (authentication failure should fail fast without retry)
            assert mock_messages.create.call_count == 1

@pytest.mark.asyncio
async def test_claude_adapter_no_tool_use_block():
    mock_client = MagicMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    # Returns normal text instead of tool call
    mock_response = MagicMock()
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
    mock_text = MagicMock()
    mock_text.type = "text"
    mock_text.text = "Hello, I am text!"
    mock_response.content = [mock_text]
    mock_messages.create.return_value = mock_response
    
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            adapter = ClaudeLLMAdapter()
            with pytest.raises(LLMResponseParsingException):
                await adapter.generate_structured_output(
                    system_prompt="sys",
                    user_prompt="user",
                    schema={}
                )

@pytest.mark.asyncio
async def test_claude_adapter_health():
    mock_client = MagicMock()
    mock_messages = AsyncMock()
    mock_client.messages = mock_messages
    
    mock_messages.create.return_value = MagicMock()
    
    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        with patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            adapter = ClaudeLLMAdapter()
            res = await adapter.check_health()
            assert res is True
            
            # Health check failure
            mock_messages.create.side_effect = Exception("failed connect")
            res_fail = await adapter.check_health()
            assert res_fail is False
