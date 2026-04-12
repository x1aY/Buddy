"""LLM module - unified interface for large language models

Structure:
- base.py - BaseLLMService abstract base class
- factory.py - create_llm_service, get_llm_service factory functions
- pipeline.py - LlmPipeline with tool calling loop
- conversation_history.py - ConversationHistory manager
- embedding.py - EmbeddingService for text embeddings
- providers/ - concrete provider implementations
"""
from .base import BaseLLMService
from .factory import create_llm_service, get_llm_service
from .pipeline import LlmPipeline
from .conversation_history import ConversationHistory
from .embedding import EmbeddingService, get_embedding_service

__all__ = [
    'BaseLLMService',
    'create_llm_service',
    'get_llm_service',
    'LlmPipeline',
    'ConversationHistory',
    'EmbeddingService',
    'get_embedding_service',
]
