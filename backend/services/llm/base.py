"""
Base LLM Service - Abstract base class defining the unified interface
All LLM provider implementations must inherit from this class
"""
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Optional
from models.schemas import LLMMessage
from services.tool_calling.tool_definitions import ToolDefinition


class BaseLLMService(ABC):
    """Abstract base class for LLM services

    All LLM providers must implement this interface to be compatible with
    the unified LLM pipeline and factory.
    """

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this service is properly configured with credentials

        Returns:
            True if configured and ready to use, False otherwise
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolDefinition]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completions from the LLM service

        Args:
            messages: List of LLM messages in internal format
            tools: Optional list of tool definitions for function calling

        Yields:
            Tokens one by one as strings. Tool calls are yielded in special
            format: [TOOL_CALL]:{json}
        """
        pass
