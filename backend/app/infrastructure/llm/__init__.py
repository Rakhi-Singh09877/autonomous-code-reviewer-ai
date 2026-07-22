"""
LLM infrastructure adapters.

Exports the GroqLLMAdapter — the primary LLMPort implementation backed by
the Groq API via the OpenAI-compatible endpoint.
"""

from app.infrastructure.llm.groq import GroqLLMAdapter

__all__ = ["GroqLLMAdapter"]
