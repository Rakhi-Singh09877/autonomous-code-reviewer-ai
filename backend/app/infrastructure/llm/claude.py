import logging
from typing import Dict, Any, Tuple
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.domain.exceptions.agent_exceptions import (
    LLMException,
    LLMConnectionException,
    LLMRateLimitException,
    LLMInvalidAPIKeyException,
    LLMResponseParsingException
)
from app.domain.models.report import TokenUsageMetadata
from app.use_cases.interfaces.llm_port import LLMPort

logger = logging.getLogger("app.infrastructure.llm.claude")

class ClaudeLLMAdapter(LLMPort):
    """
    Infrastructure Adapter implementing LLMPort for Anthropic Claude.
    Encapsulates all Anthropic SDK client calls and exceptions.
    """

    def __init__(self) -> None:
        api_key = settings.ANTHROPIC_API_KEY
        self._model = settings.REVIEW_MODEL
        self._temperature = settings.REVIEW_TEMPERATURE
        self._max_tokens = settings.REVIEW_MAX_TOKENS
        
        # Initialize the AsyncAnthropic client safely
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY is not configured in settings.")
            self._client = None
        else:
            self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], TokenUsageMetadata]:
        """
        Sends prompts to Claude and forces response matching the requested schema.
        Tracks token usage and computes real-time execution costs.
        """
        if not self._client:
            raise LLMInvalidAPIKeyException("Anthropic API client is not initialized due to missing API Key.")

        return await self._call_api_with_retry(system_prompt, user_prompt, schema)

    @retry(
        reraise=True,
        stop=stop_after_attempt(settings.REVIEW_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMRateLimitException, LLMConnectionException))
    )
    async def _call_api_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], TokenUsageMetadata]:
        """
        Helper method executed under the tenacity retry loop.
        """
        try:
            # Force tool call output matching the schema shape
            tools = [
                {
                    "name": "submit_review_issues",
                    "description": "Submit a structured collection of issues identified from review.",
                    "input_schema": schema
                }
            ]
            tool_choice = {"type": "tool", "name": "submit_review_issues"}

            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=tools,
                tool_choice=tool_choice,
                timeout=settings.REVIEW_TIMEOUT_SEC
            )

            # Process response and capture token counts
            usage = response.usage
            prompt_tokens = usage.input_tokens
            completion_tokens = usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            # Compute cost in USD
            cost_usd = (
                (prompt_tokens * settings.REVIEW_COST_INPUT_1M) +
                (completion_tokens * settings.REVIEW_COST_OUTPUT_1M)
            ) / 1_000_000.0

            token_usage = TokenUsageMetadata(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost_usd
            )

            # Extract tool use payload
            tool_use_block = None
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_use_block = content_block
                    break

            if not tool_use_block:
                raise LLMResponseParsingException("Claude response did not contain the forced tool use block.")

            # The SDK automatically decodes the inputs dictionary
            output_data = tool_use_block.input
            if not isinstance(output_data, dict):
                raise LLMResponseParsingException(f"Invalid tool use format returned: {type(output_data)}")

            return output_data, token_usage

        except anthropic.RateLimitError as e:
            logger.warning("Anthropic RateLimitError encountered, retrying...")
            raise LLMRateLimitException(f"Anthropic API rate limit: {str(e)}") from e

        except anthropic.APIConnectionError as e:
            logger.warning("Anthropic APIConnectionError encountered, retrying...")
            raise LLMConnectionException(f"Anthropic connection failed: {str(e)}") from e

        except anthropic.AuthenticationError as e:
            logger.error("Anthropic AuthenticationError: Invalid API Key.")
            raise LLMInvalidAPIKeyException(f"Anthropic API key is invalid: {str(e)}") from e

        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic APIStatusError status={e.status_code}: {str(e)}")
            raise LLMException(f"Anthropic API status error {e.status_code}: {str(e)}") from e

        except LLMResponseParsingException:
            # Propagate parsing exception directly without infinite retries
            raise

        except Exception as e:
            logger.exception("Unexpected error inside LLM execution adapter.")
            raise LLMException(f"Unexpected error executing LLM: {str(e)}") from e

    async def check_health(self) -> bool:
        """
        Attempts a basic diagnostic check with Claude.
        """
        if not self._client:
            return False
        try:
            # Execute a lightweight prompt to test connection
            await self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.warning(f"Claude health check failed: {str(e)}")
            return False
