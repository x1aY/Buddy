import base64
import httpx
from typing import Optional
from config import settings
from models.schemas import TTSResult


class TTSService:
    """Alibaba Cloud TTS Service"""

    TTS_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"

    @classmethod
    async def synthesize(cls, text: str) -> TTSResult:
        if not settings.alibaba_tts_appkey or not settings.alibaba_tts_token:
            return TTSResult(audio=b"", success=False)

        params = {
            "appkey": settings.alibaba_tts_appkey,
            "token": settings.alibaba_tts_token,
            "text": text,
            "format": "mp3",
            "sample_rate": 24000
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(cls.TTS_URL, data=params, timeout=30)
            if response.status_code != 200:
                return TTSResult(audio=b"", success=False)

            return TTSResult(audio=response.content, success=True)
