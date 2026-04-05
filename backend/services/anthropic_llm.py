"""
Anthropic Messages API protocol compatible LLM Service
https://docs.anthropic.com/en/api/messages-streaming
"""
import json
import httpx
from typing import List, AsyncGenerator
from config import settings
from models.schemas import LLMMessage, LLMContentPart


class AnthropicLLMService:
    """Anthropic Messages API protocol compatible LLM service"""

    def __init__(self):
        self.base_url = settings.anthropic_base_url
        self.auth_token = settings.anthropic_auth_token
        self.model = settings.anthropic_model

    def is_configured(self) -> bool:
        """Check if this service is properly configured"""
        return self.auth_token is not None and self.auth_token != ""

    async def chat_stream(self, messages: List[LLMMessage]) -> AsyncGenerator[str, None]:
        """Stream chat completions from Anthropic-compatible API"""
        if not self.is_configured():
            yield "Error: Anthropic auth token not configured"
            return

        headers = {
            "x-api-key": self.auth_token,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Convert internal LLMMessage to Anthropic format
        anthropic_messages = []
        system_message = None

        for msg in messages:
            if msg.role == "system":
                # Anthropic puts system in top-level parameter
                if isinstance(msg.content, str):
                    system_message = msg.content
                continue

            anthropic_msg = self._convert_message(msg)
            if anthropic_msg:
                anthropic_messages.append(anthropic_msg)

        data = {
            "model": self.model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": 4096
        }

        if system_message:
            data["system"] = system_message

        url = f"{self.base_url.rstrip('/')}/v1/messages"

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('POST', url, headers=headers, json=data) as response:
                if response.status_code != 200:
                    yield f"Error: {response.status_code}"
                    return

                async for token in self._parse_anthropic_stream(response):
                    yield token

    def _convert_message(self, msg: LLMMessage) -> dict:
        """Convert internal LLMMessage to Anthropic message format"""
        role = msg.role
        if role == "model":
            role = "assistant"  # Anthropic uses assistant, internal uses model for history

        if isinstance(msg.content, str):
            return {
                "role": role,
                "content": msg.content
            }
        else:
            # Multi-modal content with images
            content = []
            for part in msg.content:
                if part.type == "text" and part.text:
                    content.append({
                        "type": "text",
                        "text": part.text
                    })
                elif part.type == "image" and part.image:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": part.image
                        }
                    })
            return {
                "role": role,
                "content": content
            }

    async def _parse_anthropic_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """Parse Anthropic SSE streaming response

        Extracts text from content_block_delta events.
        Yields tokens one by one.
        """
        event_type = None
        async for line in response.aiter_lines():
            if not line:
                continue

            if line.startswith("event: "):
                current_event = line[7:].strip()
                event_type = current_event
                continue
            elif line.startswith("data: "):
                data_line = line[6:].strip()
                if not data_line:
                    continue

                # Only process content_block_delta events for text delta
                if event_type != "content_block_delta":
                    continue

                try:
                    chunk = json.loads(data_line)
                    if "delta" in chunk and "text" in chunk["delta"]:
                        text = chunk["delta"]["text"]
                        yield text
                except json.JSONDecodeError:
                    continue
