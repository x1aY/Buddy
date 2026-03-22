"""Test ASR service."""

import pytest
from unittest.mock import patch, AsyncMock

from services.asr import ASRService
from models.schemas import ASRResult


@pytest.mark.asyncio
async def test_asr_recognize_missing_config():
    """Test ASR recognition when appkey or token is missing."""
    # With missing config, should return failed result immediately
    with patch("services.asr.settings") as mock_settings:
        mock_settings.alibaba_asr_appkey = None
        mock_settings.alibaba_asr_token = None

        result = await ASRService.recognize("dummy_audio_data")
        assert isinstance(result, ASRResult)
        assert result.success is False
        assert result.text == ""


@pytest.mark.asyncio
async def test_asr_recognize_valid_config_but_bad_response():
    """Test ASR recognition with valid config but bad API response."""
    with patch("services.asr.settings") as mock_settings:
        mock_settings.alibaba_asr_appkey = "test_appkey"
        mock_settings.alibaba_asr_token = "test_token"

        with patch("services.asr._client.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_post.return_value = mock_response

            # Use a valid base64 string that won't cause padding errors
            result = await ASRService.recognize("ZHVtbXk=")  # "dummy" in base64
            assert result.success is False
            assert result.text == ""
