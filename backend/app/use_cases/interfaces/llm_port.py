from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from app.domain.models.report import TokenUsageMetadata

class LLMPort(ABC):
    """
    Interface Port defining methods for LLM interactions.
    Does not depend on any specific LLM library like Anthropic.
    """
    @abstractmethod
    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], TokenUsageMetadata]:
        """
        Sends system and user prompts to the LLM, forcing the response to conform
        to the provided JSON schema. Returns the parsed dictionary and token usage.
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Verifies that the LLM connection is healthy and functional.
        """
        pass
