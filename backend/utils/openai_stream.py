import json
from typing import AsyncGenerator
from httpx import Response


async def parse_openai_stream(
    response: Response,
) -> AsyncGenerator[str, None]:
    """Parse OpenAI-compatible SSE streaming response.

    Yields tokens one by one from the response stream.
    Handles the standard OpenAI chunk format:
    data: { "choices": [ { "delta": { "content": "token" } } ] }
    data: [DONE]
    """
    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        data_line = line[6:].strip()
        if data_line == "[DONE]":
            break
        try:
            chunk = json.loads(data_line)
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    yield delta["content"]
        except json.JSONDecodeError:
            continue
