import base64
import httpx
from config import settings
from models.schemas import TTSResult
from ..base import BaseTTSService

# Shared httpx client reused across requests
_client = httpx.AsyncClient(timeout=30)


class AliyunTTSService(BaseTTSService):
    """Alibaba Cloud TTS Service"""

    TTS_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"

    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        return (
            settings.alibaba_tts_appkey is not None and
            settings.alibaba_tts_appkey != "" and
            settings.alibaba_tts_token is not None and
            settings.alibaba_tts_token != ""
        )

    async def synthesize(self, text: str) -> TTSResult:
        if not self.is_configured():
            return TTSResult(audio=b"", success=False)

        params = {
            "appkey": settings.alibaba_tts_appkey,
            "token": settings.alibaba_tts_token,
            "text": text,
            "format": "mp3",
            "sample_rate": 24000
        }

        response = await _client.post(self.TTS_URL, data=params)
        if response.status_code != 200:
            return TTSResult(audio=b"", success=False)

        return TTSResult(audio=response.content, success=True)
