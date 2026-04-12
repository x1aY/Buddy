"""
Speech service factory - automatically selects configured ASR/TTSService
Selection priority: Currently only supports Alibaba Cloud, will support more in future
"""
from .base import BaseASRService, BaseTTSService
from .providers.aliyun_asr import AliyunASRService
from .providers.aliyun_tts import AliyunTTSService
from utils.logger import get_logger

logger = get_logger("speech_factory")

# Singleton instances
_asr_service: BaseASRService | None = None
_tts_service: BaseTTSService | None = None


def create_asr_service() -> BaseASRService:
    """Create a new ASR service instance, selects the first configured provider

    Selection priority: Alibaba Cloud (currently only one)
    """
    # Try Alibaba Cloud
    asr = AliyunASRService()
    if asr.is_configured():
        logger.info("asr_factory_selected_aliyun")
        return asr

    # Fallback - still return the instance, it will just fail gracefully
    logger.warning("no_asr_service_configured")
    return asr


def get_asr_service() -> BaseASRService:
    """Get the singleton ASR service instance"""
    global _asr_service
    if _asr_service is None:
        _asr_service = create_asr_service()
    return _asr_service


def create_tts_service() -> BaseTTSService:
    """Create a new TTS service instance, selects the first configured provider

    Selection priority: Alibaba Cloud (currently only one)
    """
    # Try Alibaba Cloud
    tts = AliyunTTSService()
    if tts.is_configured():
        logger.info("tts_factory_selected_aliyun")
        return tts

    # Fallback - still return the instance, it will just fail gracefully
    logger.warning("no_tts_service_configured")
    return tts


def get_tts_service() -> BaseTTSService:
    """Get the singleton TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = create_tts_service()
    return _tts_service
