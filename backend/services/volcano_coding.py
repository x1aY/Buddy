import json
import hashlib
import hmac
import time
from typing import List, AsyncGenerator
import httpx
from config import settings
from models.schemas import LLMMessage
from utils import parse_openai_stream


class VolcanoCodingService:
    """Volcano Engine Coding Plan Service"""

    BASE_HOST = "code.volcengine.com"

    def __init__(self):
        self.access_key = settings.volcano_access_key
        self.secret_key = settings.volcano_secret_key
        self.region = settings.volcano_region

    def _sign(self, method: str, path: str, query: dict, body: dict) -> tuple[str, str]:
        """Sign request with Volcano credentials"""
        timestamp = str(int(time.time()))
        # Sort query params
        sorted_keys = sorted(query.keys())
        canonical_query = '&'.join([f"{k}={query[k]}" for k in sorted_keys])

        # Create canonical request
        canonical_request = f"{method}\n{path}\n{canonical_query}\n\n{json.dumps(body)}"

        # Calculate signature
        signing_key = hmac.new(self.secret_key.encode('utf-8'), timestamp.encode('utf-8'), hashlib.sha256).digest()
        signature = hmac.new(signing_key, canonical_request.encode('utf-8'), hashlib.sha256).hexdigest()

        return signature, timestamp

    async def chat_stream(self, messages: List[LLMMessage], model: str = "volcano-coding-32k") -> AsyncGenerator[str, None]:
        """Stream chat completions from Volcano Engine Coding Plan"""
        if not self.access_key or not self.secret_key:
            yield "Error: Volcano Engine credentials not configured"
            return

        url_path = "/api/v1/chat/completions"
        query = {
            "access_key": self.access_key,
        }

        # Convert messages to Volcano format
        volcano_messages = []
        for msg in messages:
            if isinstance(msg.content, str):
                volcano_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            else:
                # Handle multi-modal if needed
                content = "".join([p.text or "" for p in msg.content if p.text])
                volcano_messages.append({
                    "role": msg.role,
                    "content": content
                })

        body = {
            "model": model,
            "messages": volcano_messages,
            "stream": True,
            "temperature": 0.2
        }

        signature, timestamp = self._sign("POST", url_path, query, body)
        query["signature"] = signature
        query["timestamp"] = timestamp

        full_url = f"https://{self.region}.{self.BASE_HOST}{url_path}"

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream('POST', full_url, params=query, json=body) as response:
                if response.status_code != 200:
                    yield f"Error: HTTP {response.status_code}"
                    return

                async for token in parse_openai_stream(response):
                    yield token
