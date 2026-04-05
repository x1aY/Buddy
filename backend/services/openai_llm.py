import httpx
from typing import List, AsyncGenerator
from config import settings
from models.schemas import LLMMessage, LLMContentPart
from utils import parse_openai_stream


class OpenAILLMService:
    """OpenAI Chat Completions protocol compatible LLM service

    Works with:
    - Official OpenAI API
    - Doubao (ByteDance)
    - Any other service with OpenAI-compatible endpoint
    """

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model

    def is_configured(self) -> bool:
        """Check if this service is properly configured"""
        return self.api_key is not None and self.api_key != ""

    async def chat_stream(self, messages: List[LLMMessage]) -> AsyncGenerator[str, None]:
        """Stream chat completions from OpenAI-compatible API"""
        if not self.is_configured():
            yield "Error: OpenAI API key not configured"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            role = msg.role
            if role == "model":
                role = "assistant"  # Map internal role name to OpenAI

            if isinstance(msg.content, str):
                openai_messages.append({
                    "role": role,
                    "content": msg.content
                })
            else:
                # Handle multi-modal content with images
                content = []
                for part in msg.content:
                    if part.type == "text" and part.text:
                        content.append({
                            "type": "text",
                            "text": part.text
                        })
                    elif part.type == "image" and part.image:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{part.image}"
                            }
                        })
                openai_messages.append({
                    "role": role,
                    "content": content
                })

        data = {
            "model": self.model,
            "messages": openai_messages,
            "stream": True,
            "temperature": 0.7
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('POST', url, headers=headers, json=data) as response:
                if response.status_code != 200:
                    yield f"Error: {response.status_code}"
                    return

                async for token in parse_openai_stream(response):
                    yield token
