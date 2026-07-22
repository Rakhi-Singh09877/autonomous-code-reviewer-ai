import logging
from typing import Dict, Any, Tuple

# OpenAI Python SDK – configured to point at the Groq API endpoint
from openai import AsyncOpenAI
from openai import (
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    APIStatusError,
)

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.domain.exceptions.agent_exceptions import (
    LLMException,
    LLMConnectionException,
    LLMRateLimitException,
    LLMInvalidAPIKeyException,
    LLMResponseParsingException,
)
from app.domain.models.report import TokenUsageMetadata
from app.use_cases.interfaces.llm_port import LLMPort

logger = logging.getLogger("app.infrastructure.llm.groq")


class GroqLLMAdapter(LLMPort):
    """
    Infrastructure Adapter implementing LLMPort for the Groq cloud platform.

    Uses the OpenAI Python SDK pointed at Groq's OpenAI-compatible endpoint
    (https://api.groq.com/openai/v1).  Groq serves open-weight models such as
    ``openai/gpt-oss-120b`` with extremely low latency.

    The adapter preserves the same contract (LLMPort) as the previous Claude
    adapter so that ReviewAgent, RepositoryAnalysisOrchestrator, and every
    other consumer require zero changes.

    Key behaviours preserved:
    - ``generate_structured_output()`` forces JSON output via OpenAI's function‑calling
      (tool_choice) mechanism, matching the original Anthropic tool_use flow.
    - ``TokenUsageMetadata`` collects prompt/completion tokens and estimates cost
      using the configurable per‑1M‑token rates.
    - Retry logic via tenacity covers transient failures (rate‑limits, network).
    - Comprehensive logging at INFO / WARNING / ERROR levels.
    - Async API – the OpenAI SDK's ``AsyncOpenAI`` is used throughout.
    - ``check_health()`` sends a trivial ping to verify connectivity.
    """

    def __init__(self) -> None:
        """
        Initialise the Groq adapter.

        Reads ``GROQ_API_KEY`` from application settings.  If the key is
        missing the client is set to ``None`` and any call will raise
        ``LLMInvalidAPIKeyException`` early (fail‑fast).
        """
        api_key = settings.GROQ_API_KEY
        self._model = settings.GROQ_MODEL
        self._temperature = settings.REVIEW_TEMPERATURE
        self._max_tokens = settings.REVIEW_MAX_TOKENS

        if not api_key:
            logger.warning("GROQ_API_KEY is not configured in settings.")
            self._client: AsyncOpenAI | None = None
        else:
            # Point the OpenAI SDK at Groq's OpenAI‑compatible base URL
            self._client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key,
            )
            logger.info(
                "GroqLLMAdapter initialised – model=%s, base_url=%s",
                self._model,
                "https://api.groq.com/openai/v1",
            )

    # ------------------------------------------------------------------
    # Public interface – LLMPort
    # ------------------------------------------------------------------

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], TokenUsageMetadata]:
        """
        Send prompts to Groq and force the response to match **schema**.

        Internally we declare an OpenAI function tool whose ``parameters``
        field is the provided JSON Schema.  By setting ``tool_choice`` to
        that function we guarantee that the model returns a well‑formed
        JSON object inside a tool‑call message.
        """
        if self._client is None:
            raise LLMInvalidAPIKeyException(
                "Groq API client is not initialised – GROQ_API_KEY is missing."
            )

        return await self._call_api_with_retry(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )

    async def check_health(self) -> bool:
        """
        Diagnostic ping – sends a trivial request to Groq and reports
        whether the API is reachable and the credentials are valid.
        """
        if self._client is None:
            logger.warning("Health check skipped – client not initialised.")
            return False

        try:
            await self._client.chat.completions.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
                timeout=5.0,
            )
            return True
        except Exception as exc:
            logger.warning("Groq health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(settings.REVIEW_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (LLMRateLimitException, LLMConnectionException)
        ),
    )
    async def _call_api_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], TokenUsageMetadata]:
        """
        Core API call wrapped in a tenacity retry loop.

        Transient failures (rate‑limits, network blips) are retried
        automatically; permanent errors (bad key, invalid schema) are
        raised immediately so that the caller sees them without delay.
        """
        try:
            # ------------------------------------------------------------------
            # Build OpenAI function‑calling tool matching the requested schema.
            # This is the direct equivalent of Anthropic's ``tool_use`` block.
            # ------------------------------------------------------------------
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "submit_review_issues",
                        "description": (
                            "Submit a structured collection of issues "
                            "identified during code review."
                        ),
                        "parameters": schema,
                    },
                }
            ]

            # Force the model to call our tool on every response – this
            # guarantees a JSON object that matches the schema.
            tool_choice = {
                "type": "function",
                "function": {"name": "submit_review_issues"},
            }

            # Compose the message list.  The ``system`` role is sent as
            # the first message with role "system"; the user prompt follows.
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            logger.debug(
                "Calling Groq chat.completions.create – model=%s, "
                "prompt_tokens_est=%d",
                self._model,
                len(system_prompt + user_prompt) // 4,
            )

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                tools=tools,
                tool_choice=tool_choice,
                timeout=settings.REVIEW_TIMEOUT_SEC,
            )

            # ------------------------------------------------------------------
            # Extract token usage and compute cost
            # ------------------------------------------------------------------
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else prompt_tokens + completion_tokens

            cost_usd = (
                (prompt_tokens * settings.REVIEW_COST_INPUT_1M)
                + (completion_tokens * settings.REVIEW_COST_OUTPUT_1M)
            ) / 1_000_000.0

            token_usage = TokenUsageMetadata(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost_usd,
            )

            logger.debug(
                "Groq tokens – prompt=%d, completion=%d, cost=$%.6f",
                prompt_tokens,
                completion_tokens,
                cost_usd,
            )

            # ------------------------------------------------------------------
            # Parse the tool‑call payload from the response
            # ------------------------------------------------------------------
            choice = response.choices[0]
            message = choice.message

            if not message.tool_calls:
                raise LLMResponseParsingException(
                    "Groq response did not contain the expected tool_call block."
                )

            # We forced a single tool call, so grab the first one.
            tool_call = message.tool_calls[0]
            if tool_call.function.name != "submit_review_issues":
                logger.warning(
                    "Unexpected tool call name: %s (expected submit_review_issues)",
                    tool_call.function.name,
                )

            # ``tool_call.function.arguments`` is a JSON string; parse it.
            import json

            try:
                output_data = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as exc:
                raise LLMResponseParsingException(
                    f"Failed to decode tool-call arguments as JSON: {exc}"
                ) from exc

            if not isinstance(output_data, dict):
                raise LLMResponseParsingException(
                    f"Invalid tool‑call payload type: {type(output_data)} – expected dict"
                )

            return output_data, token_usage

        # ------------------------------------------------------------------
        # Translate OpenAI SDK exceptions into our domain exceptions
        # ------------------------------------------------------------------
        except RateLimitError as exc:
            logger.warning(
                "Groq RateLimitError encountered (status=%s) – retrying...",
                getattr(exc, "status_code", "?"),
            )
            raise LLMRateLimitException(
                f"Groq API rate limit exceeded: {exc}"
            ) from exc

        except APIConnectionError as exc:
            logger.warning(
                "Groq APIConnectionError encountered – retrying..."
            )
            raise LLMConnectionException(
                f"Groq connection failed: {exc}"
            ) from exc

        except AuthenticationError as exc:
            logger.error(
                "Groq AuthenticationError – check GROQ_API_KEY"
            )
            raise LLMInvalidAPIKeyException(
                f"Groq API key is invalid: {exc}"
            ) from exc

        except APIStatusError as exc:
            logger.error(
                "Groq APIStatusError status=%s body=%s",
                exc.status_code,
                exc.body if hasattr(exc, "body") else str(exc),
            )
            raise LLMException(
                f"Groq API status error {exc.status_code}: {exc}"
            ) from exc

        except LLMResponseParsingException:
            # Re‑raise parsing errors immediately – retries won't help here.
            raise

        except Exception as exc:
            logger.exception("Unexpected error inside Groq LLM adapter.")
            raise LLMException(
                f"Unexpected error executing Groq LLM: {exc}"
            ) from exc
