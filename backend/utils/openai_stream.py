import json
from typing import AsyncGenerator, Optional, Tuple
from httpx import Response
from utils.logger import get_logger

logger = get_logger("openai_stream_parser")


def _try_parse_arguments(tool_arguments: str) -> Tuple[bool, dict]:
    """Try to parse tool arguments with error recovery.

    Attempts two parsing strategies:
    1. Direct parse (normal case)
    2. If that fails, fix common JSON streaming issues (missing braces, trailing commas)

    Args:
        tool_arguments: Accumulated JSON string to parse

    Returns:
        (parsed: bool, arguments: dict) - whether parsing succeeded and the result
    """
    arguments = {}
    parsed = False

    if not tool_arguments:
        return parsed, arguments

    for attempt in [1, 2]:
        try:
            if attempt == 1:
                arguments = json.loads(tool_arguments)
            else:
                # Second attempt - fix common JSON streaming issues
                fixed_args = tool_arguments.strip()
                # If it ends with comma, remove it
                if fixed_args.endswith(','):
                    fixed_args = fixed_args[:-1]
                # If it doesn't start with {, add it
                if not fixed_args.startswith('{'):
                    fixed_args = '{' + fixed_args
                # If it doesn't end with }, add it
                if not fixed_args.endswith('}'):
                    fixed_args = fixed_args + '}'
                arguments = json.loads(fixed_args)
            parsed = True
            break
        except json.JSONDecodeError:
            continue

    return parsed, arguments


async def parse_openai_stream(
    response: Response,
) -> AsyncGenerator[str, None]:
    """Parse OpenAI-compatible SSE streaming response.

    Yields tokens one by one from the response stream.
    Handles the standard OpenAI chunk format:
    data: { "choices": [ { "delta": { "content": "token" } } ] }
    data: [DONE]

    Also handles tool calls in the format:
    data: { "choices": [ { "delta": { "tool_calls": [ ... ] } } ] }

    When a complete tool call is detected, yields it in the format:
    [TOOL_CALL]:{"type": "tool_call", "id": "...", "name": "...", "parameters": {...}}
    """
    # Track current tool call being built
    current_tool_call: Optional[bool] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: str = ""
    has_tool_call: bool = False

    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        data_line = line[6:].strip()
        if not data_line:
            continue

        if data_line == "[DONE]":
            # If tool call was in progress but stream ended, try to yield what we have
            if has_tool_call and current_tool_call:
                if tool_arguments:
                    parsed, arguments = _try_parse_arguments(tool_arguments)
                    if parsed:
                        tool_call_event = {
                            "type": "tool_call",
                            "id": tool_call_id or "",
                            "name": tool_name or "",
                            "parameters": arguments
                        }
                        yield f"[TOOL_CALL]:{json.dumps(tool_call_event, ensure_ascii=False)}"
                    else:
                        logger.warning("failed_to_parse_final_tool_call", arguments=tool_arguments)
                # Always reset even on failure
                current_tool_call = None
                tool_call_id = None
                tool_name = None
                tool_arguments = ""
                has_tool_call = False
            break

        try:
            chunk = json.loads(data_line)
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})

                # Handle text delta (normal content)
                if "content" in delta and delta["content"] is not None:
                    yield delta["content"]

                # Handle tool calls
                if "tool_calls" in delta:
                    tool_calls = delta["tool_calls"]
                    if tool_calls and len(tool_calls) > 0:
                        has_tool_call = True
                        tool_call = tool_calls[0]

                        # Start of a new tool call
                        if "id" in tool_call and tool_call["id"] is not None:
                            tool_call_id = tool_call["id"]

                        if "function" in tool_call:
                            function = tool_call["function"]

                            if "name" in function and function["name"] is not None:
                                tool_name = function["name"]

                            if "arguments" in function and function["arguments"] is not None:
                                tool_arguments += function["arguments"]

                            # If we have all required fields, track that we're building a tool call
                            if tool_call_id and tool_name:
                                current_tool_call = True

            # Check for tool call completion using multiple conditions:
            # 1. finish_reason == "tool_calls" (standard case)
            # 2. OR the accumulated arguments appear to be complete (starts with { and ends with })
            if "choices" in chunk and len(chunk["choices"]) > 0:
                choice = chunk["choices"][0]
                finish_reason = choice.get("finish_reason")

                # Check if we should complete the tool call
                should_complete = False

                # Condition 1: explicit finish reason for tool_calls
                if finish_reason == "tool_calls" and current_tool_call:
                    should_complete = True

                # Condition 2: check if accumulated arguments look complete
                if current_tool_call and tool_arguments:
                    trimmed = tool_arguments.strip()
                    if trimmed.startswith('{') and trimmed.endswith('}'):
                        # Try a test parse to see if it's valid JSON
                        try:
                            json.loads(trimmed)
                            # If it parses correctly and we have all required fields, complete it
                            if tool_call_id and tool_name:
                                should_complete = True
                        except json.JSONDecodeError:
                            pass

                if should_complete and current_tool_call:
                    # Try to parse with recovery
                    parsed, arguments = _try_parse_arguments(tool_arguments)
                    if parsed:
                        tool_call_event = {
                            "type": "tool_call",
                            "id": tool_call_id or "",
                            "name": tool_name or "",
                            "parameters": arguments
                        }
                        yield f"[TOOL_CALL]:{json.dumps(tool_call_event, ensure_ascii=False)}"

                    # ALWAYS reset regardless of parsing success
                    # This prevents leftover state from corrupting future tool calls
                    current_tool_call = None
                    tool_call_id = None
                    tool_name = None
                    tool_arguments = ""
                    has_tool_call = False

        except json.JSONDecodeError as e:
            logger.warning("invalid_json_in_openai_stream", error=str(e), line=data_line[:100])
            continue
