import httpx
from typing import List, AsyncGenerator
from config import settings
from models.schemas import LLMMessage, LLMContentPart
from utils import parse_openai_stream


class DoubaoLLMService:
    """Doubao LLM Service"""

    def __init__(self):
        self.api_key = settings.doubao_api_key
        self.endpoint = settings.doubao_endpoint

    async def chat_stream(self, messages: List[LLMMessage]) -> AsyncGenerator[str, None]:
        """Stream chat completions from Doubao"""
        if not self.api_key:
            yield "Error: Doubao API key not configured"
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            if isinstance(msg.content, str):
                openai_messages.append({
                    "role": msg.role,
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
                    "role": msg.role,
                    "content": content
                })

        data = {
            "model": "doubao-vision-pro",
            "messages": openai_messages,
            "stream": True,
            "temperature": 0.7
        }

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('POST', self.endpoint, headers=headers, json=data) as response:
                if response.status_code != 200:
                    yield f"Error: {response.status_code}"
                    return

                async for token in parse_openai_stream(response):
                    yield token
