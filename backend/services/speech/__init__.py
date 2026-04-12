"""Speech module - unified interface for ASR and TTS

Structure:
- base.py - BaseASRService, BaseTTSService abstract base classes
- factory.py - create_asr_service, get_asr_service, create_tts_service, get_tts_service factories
- asr_stream_processor.py - AsrStreamProcessor for streaming ASR with silence detection
- providers/ - concrete provider implementations (currently all Alibaba Cloud)
"""
from .base import BaseASRService, BaseTTSService
from .factory import (
    create_asr_service,
    get_asr_service,
    create_tts_service,
    get_tts_service,
)
from .asr_stream_processor import AsrStreamProcessor

__all__ = [
    'BaseASRService',
    'BaseTTSService',
    'create_asr_service',
    'get_asr_service',
    'create_tts_service',
    'get_tts_service',
    'AsrStreamProcessor',
]
