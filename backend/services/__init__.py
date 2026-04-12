"""
Services module - organized by functional groups:
- llm/ - Large Language Models (unified interface with multiple providers)
- speech/ - Speech processing (ASR and TTS)
- auth/ - Third-party OAuth authentication
- chat_session.py - WebSocket chat session coordinator (handles all client messages)
"""
# Re-export from new locations for backward compatibility
from .auth.huawei_oauth import HuaweiOAuthService
from .auth.wechat_oauth import WeChatOAuthService
from .speech.providers.aliyun_asr import AliyunASRService as ASRService
from .speech.providers.aliyun_tts import AliyunTTSService as TTSService
from .llm.base import BaseLLMService
from .llm.providers.anthropic import AnthropicLLMService
from .llm.providers.openai import OpenAILLMService
from .llm.providers.volcengine import VolcengineLLMService
from .llm.factory import create_llm_service, get_llm_service
from .chat_session import StreamProcessor

# Also export the new grouped modules for cleaner imports
from .llm import (
    BaseLLMService,
    create_llm_service,
    get_llm_service,
    LlmPipeline,
    ConversationHistory,
    EmbeddingService,
    get_embedding_service,
)
from .speech import (
    BaseASRService,
    BaseTTSService,
    create_asr_service,
    get_asr_service,
    create_tts_service,
    get_tts_service,
    AsrStreamProcessor,
)
from .auth import (
    HuaweiOAuthService,
    WeChatOAuthService,
)

__all__ = [
    # Original exports for backward compatibility
    'HuaweiOAuthService',
    'WeChatOAuthService',
    'ASRService',
    'TTSService',
    'BaseLLMService',
    'AnthropicLLMService',
    'OpenAILLMService',
    'VolcengineLLMService',
    'create_llm_service',
    'get_llm_service',
    'StreamProcessor',
    # New grouped exports
    'LlmPipeline',
    'ConversationHistory',
    'EmbeddingService',
    'get_embedding_service',
    'BaseASRService',
    'BaseTTSService',
    'create_asr_service',
    'get_asr_service',
    'create_tts_service',
    'get_tts_service',
    'AsrStreamProcessor',
]
