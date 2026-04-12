"""
Anthropic Messages API protocol compatible LLM Service
https://docs.anthropic.com/en/api/messages-streaming
"""
import json
import httpx
from typing import List, AsyncGenerator, Optional
from config import settings
from models.schemas import LLMMessage, LLMContentPart
from ..base import BaseLLMService
from services.tool_calling.tool_definitions import ToolDefinition

# Constant for tool call event type
TOOL_CALL_EVENT_TYPE = "tool_call"


class AnthropicLLMService(BaseLLMService):
    """Anthropic Messages API protocol compatible LLM service"""

    def __init__(self):
        self.base_url = settings.anthropic_base_url
        self.auth_token = settings.anthropic_auth_token
        self.model = settings.anthropic_model

    def is_configured(self) -> bool:
        """Check if this service is properly configured"""
        return (
            self.auth_token is not None and
            self.auth_token != ""
        )

    async def chat_stream(self, messages: List[LLMMessage], tools: Optional[List[ToolDefinition]] = None) -> AsyncGenerator[str, None]:
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

        if tools:
            data["tools"] = [tool.to_anthropic() for tool in tools]

        # Use base_url directly as complete endpoint URL as configured
        url = self.base_url.rstrip('/')

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
        Detects tool calls and yields them in special [TOOL_CALL]:JSON format.
        Yields tokens one by one.
        """
        event_type = None
        current_tool_use = None  # Track tool use being built
        tool_use_input = ""  # Accumulate tool input JSON

        async for line in response.aiter_lines():
            if not line:
                continue

            if line.startswith("event: "):
                event_type = line[7:].strip()
                continue
            elif line.startswith("data: "):
                data_line = line[6:].strip()
                if not data_line:
                    continue

                try:
                    chunk = json.loads(data_line)

                    if event_type == "content_block_start":
                        # Check if starting a tool_use block
                        if "content_block" in chunk:
                            block = chunk["content_block"]
                            if block.get("type") == "tool_use":
                                current_tool_use = {
                                    "id": block.get("id"),
                                    "name": block.get("name"),
                                    "input": {}
                                }
                                tool_use_input = ""

                    elif event_type == "content_block_delta":
                        if "delta" in chunk:
                            delta = chunk["delta"]

                            # Handle text delta (normal content)
                            if "text" in delta:
                                text = delta["text"]
                                yield text

                            # Handle input_json delta (tool use arguments)
                            elif "partial_json" in delta and current_tool_use is not None:
                                tool_use_input += delta["partial_json"]

                    elif event_type == "content_block_stop":
                        # Tool use block complete
                        if current_tool_use is not None:
                            # Parse accumulated input JSON
                            try:
                                if tool_use_input:
                                    current_tool_use["input"] = json.loads(tool_use_input)
                            except json.JSONDecodeError:
                                # If parsing fails, keep as empty dict
                                pass

                            # Yield tool call in special format
                            tool_call_event = {
                                "type": TOOL_CALL_EVENT_TYPE,
                                "id": current_tool_use["id"],
                                "name": current_tool_use["name"],
                                "parameters": current_tool_use["input"]
                            }
                            yield f"[TOOL_CALL]:{json.dumps(tool_call_event, ensure_ascii=False)}"

                            # Reset
                            current_tool_use = None
                            tool_use_input = ""

                except json.JSONDecodeError:
                    continue
