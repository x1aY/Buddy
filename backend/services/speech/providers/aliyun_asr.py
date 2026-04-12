import base64
import httpx
from config import settings
from models.schemas import ASRResult
from ..base import BaseASRService

# Shared httpx client reused across requests
_client = httpx.AsyncClient(timeout=30)


class AliyunASRService(BaseASRService):
    """Alibaba Cloud ASR Service"""

    ASR_URL = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    def is_configured(self) -> bool:
        """Check if the service is properly configured"""
        return (
            settings.alibaba_asr_appkey is not None and
            settings.alibaba_asr_appkey != "" and
            settings.alibaba_asr_token is not None and
            settings.alibaba_asr_token != ""
        )

    async def recognize(self, audio_base64: str) -> ASRResult:
        if not self.is_configured():
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

        response = await _client.post(self.ASR_URL, params=params, content=audio_data, headers=headers)
        if response.status_code != 200:
            return ASRResult(text="", success=False)

        result = response.json()
        if result.get("status") == 20000000:
            return ASRResult(text=result.get("result", ""), success=True)
        else:
            return ASRResult(text="", success=False)
