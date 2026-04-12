"""
Abstract base classes for speech services (ASR and TTS)
All concrete implementations must implement these interfaces
"""
from abc import ABC, abstractmethod
from typing import Optional
from models.schemas import ASRResult, TTSResult


class BaseASRService(ABC):
    """Abstract base class for Automatic Speech Recognition"""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        pass

    @abstractmethod
    async def recognize(self, audio_base64: str) -> ASRResult:
        """Recognize speech from audio base64 encoded data

        Args:
            audio_base64: Base64 encoded audio data

        Returns:
            ASRResult with recognized text and success flag
        """
        pass


class BaseTTSService(ABC):
    """Abstract base class for Text-to-Speech"""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        pass

    @abstractmethod
    async def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech from text

        Args:
            text: Text to synthesize

        Returns:
            TTSResult with audio data (bytes) and success flag
        """
        pass
