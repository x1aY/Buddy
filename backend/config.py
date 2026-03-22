from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Server
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = True

    # CORS
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"

    # JWT
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    # OAuth
    huawei_client_id: Optional[str] = None
    huawei_client_secret: Optional[str] = None
    huawei_redirect_uri: Optional[str] = None

    wechat_app_id: Optional[str] = None
    wechat_app_secret: Optional[str] = None
    wechat_redirect_uri: Optional[str] = None

    # Alibaba Cloud ASR
    alibaba_asr_appkey: Optional[str] = None
    alibaba_asr_token: Optional[str] = None

    # Alibaba Cloud TTS
    alibaba_tts_appkey: Optional[str] = None
    alibaba_tts_token: Optional[str] = None

    # Doubao LLM
    doubao_api_key: Optional[str] = None
    doubao_endpoint: str = "https://aquasearch.doubao.com/api/v1/chat/completions"

    # Volcano Engine Coding Plan
    volcano_access_key: Optional[str] = None
    volcano_secret_key: Optional[str] = None
    volcano_region: str = "cn-beijing"

    class Config:
        env_file = ".env"


settings = Settings()
