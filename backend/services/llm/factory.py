"""
LLM Factory - Unified factory for creating configured LLM service instances
Automatically selects the appropriate LLM service based on environment configuration.
Priority: VolcEngine (if configured) -> Anthropic -> OpenAI
"""
from typing import Optional
from .base import BaseLLMService
from .providers.volcengine import VolcengineLLMService
from .providers.anthropic import AnthropicLLMService
from .providers.openai import OpenAILLMService
from utils.logger import get_logger

logger = get_logger("llm_factory")

# Singleton instance for reuse
_llm_instance: Optional[BaseLLMService] = None


def create_llm_service() -> BaseLLMService:
    """Create LLM service based on configuration priority

    Priority:
    1. VolcEngine (if configured)
    2. Anthropic (if configured)
    3. OpenAI (if configured)

    Returns:
        Configured LLM service instance
    """
    # Try VolcEngine first
    volcengine = VolcengineLLMService()
    if volcengine.is_configured():
        logger.info("llm_factory_selected_volcengine")
        return volcengine

    # Try Anthropic next
    anthropic = AnthropicLLMService()
    if anthropic.is_configured():
        logger.info("llm_factory_selected_anthropic")
        return anthropic

    # Fallback to OpenAI
    openai = OpenAILLMService()
    if openai.is_configured():
        logger.info("llm_factory_selected_openai")
        return openai

    # If none configured, return VolcEngine as default (it will show error message)
    logger.warning("llm_factory_no_provider_configured")
    return volcengine


def get_llm_service() -> BaseLLMService:
    """Get singleton instance of the configured LLM service

    Returns:
        Singleton LLM service instance
    """
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = create_llm_service()
    return _llm_instance
