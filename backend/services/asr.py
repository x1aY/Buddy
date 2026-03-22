import base64
import httpx
from config import settings
from models.schemas import ASRResult

# Shared httpx client reused across requests
_client = httpx.AsyncClient(timeout=30)


class ASRService:
    """Alibaba Cloud ASR Service"""

    ASR_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    @classmethod
    async def recognize(cls, audio_base64: str) -> ASRResult:
        if not settings.alibaba_asr_appkey or not settings.alibaba_asr_token:
            return ASRResult(text="", success=False)

        audio_data = base64.b64decode(audio_base64)

        params = {
            "appkey": settings.alibaba_asr_appkey,
            "format": "opus",
            "sample_rate": 16000
        }

        headers = {
            "X-NLS-Token": settings.alibaba_asr_token,
            "Content-Type": "application/octet-stream"
        }

        response = await _client.post(cls.ASR_URL, params=params, content=audio_data, headers=headers)
        if response.status_code != 200:
            return ASRResult(text="", success=False)

        result = response.json()
        if result.get("status") == 20000000:
            return ASRResult(text=result.get("result", ""), success=True)
        else:
            return ASRResult(text="", success=False)
