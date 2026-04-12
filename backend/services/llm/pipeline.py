"""
LLM Pipeline - Handles LLM execution with tool calling support
"""
import json
import re
from typing import AsyncGenerator, Optional, List

from config import settings
from models.schemas import LLMMessage, LLMContentPart, ToolCall, ToolResult
from .base import BaseLLMService
from .conversation_history import ConversationHistory
from ..speech import BaseTTSService
from services.tool_calling.tool_definitions import get_tool_definitions, ToolDefinition
from services.tool_calling.tool_executor import ToolExecutor
from services.tool_calling.open_websearch_client import OpenWebSearchClient
from utils.logger import get_logger

logger = get_logger("llm_pipeline")

# Tool call pattern - matches [TOOL_CALL]:{json}
TOOL_CALL_PATTERN = re.compile(r'^\[TOOL_CALL\]:(.+)$', re.DOTALL)


class LlmPipeline:
    """LLM Pipeline for handling conversations with tool calling support

    Uses a unified LLM service selected by llm_factory based on configuration.
    """

    def __init__(
        self,
        conversation_history: ConversationHistory,
        latest_camera_frame: Optional[str],
        llm_service: BaseLLMService,
        tts_service: BaseTTSService
    ):
        self.conversation_history = conversation_history
        self.latest_camera_frame = latest_camera_frame
        self.llm_service = llm_service
        self.tts_service = tts_service

        # Initialize tool calling components if open-websearch is enabled
        self.open_websearch_client: Optional[OpenWebSearchClient] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.tools: Optional[List[ToolDefinition]] = None

        if settings.open_websearch_enabled:
            self.open_websearch_client = OpenWebSearchClient(settings)
            self.tool_executor = ToolExecutor(self.open_websearch_client)
            self.tools = get_tool_definitions()
            logger.info("tool_calling_enabled")

    async def run(self) -> AsyncGenerator[str, None]:
        """Run the LLM pipeline with tool calling loop"""
        max_iterations = 5
        current_iteration = 0

        # Working list of messages that includes tool calls and results
        # This is separate from conversation_history which only stores user and final assistant messages
        working_messages = self._build_llm_messages()

        while current_iteration < max_iterations:
            current_iteration += 1
            logger.info("llm_iteration", iteration=current_iteration, max_iterations=max_iterations)

            # Stream response from LLM
            full_text = ""
            tool_calls: List[ToolCall] = []

            async for token in self._call_llm(working_messages):
                # Check if this token is a tool call
                tool_call = self._parse_tool_call(token)
                if tool_call:
                    # Tool call is for internal use only - DO NOT yield to frontend
                    # It will be added to working_messages but not shown to user
                    tool_calls.append(tool_call)
                else:
                    full_text += token
                    yield token

            # If no tool calls, we're done
            if not tool_calls:
                logger.info("no_tool_calls_done")
                return

            # If we have tool calls but no tools configured, stop here
            if not self.tool_executor or not self.tools:
                logger.warning("tool_calls_but_no_tools_configured")
                return

            logger.info("executing_tool_calls", count=len(tool_calls))

            # Add assistant's response (with tool calls) to working messages
            working_messages.append(self._create_assistant_message_with_tool_calls(full_text, tool_calls))

            # Execute all tool calls
            for tool_call in tool_calls:
                tool_result = await self.tool_executor.execute(tool_call)
                logger.info("tool_executed", tool_name=tool_call.name, success=tool_result.success)

                # Add tool result to working messages
                working_messages.append(self._create_tool_message(tool_result))

        # If we hit max iterations
        logger.warning("max_iterations_reached", max_iterations=max_iterations)
        yield "\n\n[已达到最大工具调用次数限制]"

    def _build_llm_messages(self) -> List[LLMMessage]:
        """Build LLM messages from conversation history"""
        messages: List[LLMMessage] = []

        # System prompt
        system_prompt = "你是一个有帮助的AI助手。"
        if self.latest_camera_frame:
            system_prompt += " 用户刚刚分享了一张摄像头画面，你可以在回答中参考它。"

        messages.append(LLMMessage(
            role="system",
            content=system_prompt
        ))

        # Convert conversation history
        for conv_msg in self.conversation_history.get_messages():
            content: str | List[LLMContentPart] = conv_msg.text

            # If this is the last user message and we have a camera frame, add it
            if conv_msg == self.conversation_history.get_messages()[-1] and conv_msg.role == "user" and self.latest_camera_frame:
                content = [
                    LLMContentPart(type="text", text=conv_msg.text),
                    LLMContentPart(type="image", image=self.latest_camera_frame)
                ]

            # Convert role: internal 'model' -> 'assistant' for LLM
            llm_role = conv_msg.role
            if llm_role == "model":
                llm_role = "assistant"
            messages.append(LLMMessage(
                role=llm_role,
                content=content
            ))

        return messages

    def _parse_tool_call(self, token: str) -> Optional[ToolCall]:
        """Parse a tool call from a token if it matches the pattern"""
        match = TOOL_CALL_PATTERN.match(token)
        if not match:
            return None

        try:
            data = json.loads(match.group(1))
            if data.get("type") == "tool_call":
                return ToolCall(
                    id=data.get("id", ""),
                    name=data.get("name", ""),
                    parameters=data.get("parameters", {})
                )
        except json.JSONDecodeError:
            logger.warning("failed_to_parse_tool_call_json", json_str=match.group(1))

        return None

    async def _call_llm(self, messages: List[LLMMessage]) -> AsyncGenerator[str, None]:
        """Call the configured LLM service"""
        logger.info("using unified llm service", configured=self.llm_service.is_configured())
        async for token in self.llm_service.chat_stream(messages, self.tools):
            yield token

    def _create_assistant_message_with_tool_calls(self, text: str, tool_calls: List[ToolCall]) -> LLMMessage:
        """Create an assistant message containing tool calls that matches LLM expectations

        For Anthropic: each tool call is a separate content block with type "tool_use"
        For OpenAI: tool calls are stored in the message content but handled through our conversion
        """
        content_parts: List[LLMContentPart] = []

        # Add any text content first if present
        if text and text.strip():
            content_parts.append(LLMContentPart(type="text", text=text.strip()))

        # For Anthropic, each tool call must be a distinct content part with proper structure
        # Our internal schema represents this as content parts
        for tool_call in tool_calls:
            # For Anthropic: the content part needs to have type "tool_use" with the tool data
            # We encode this in the content itself since our schema only has text/image types
            tool_data = {
                "type": "tool_use",
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.parameters
            }
            content_parts.append(LLMContentPart(type="text", text=json.dumps(tool_data)))

        if len(content_parts) == 1:
            # If only one part, return as simple string
            return LLMMessage(
                role="assistant",
                content=content_parts[0].text
            )

        return LLMMessage(
            role="assistant",
            content=content_parts
        )

    def _create_tool_message(self, tool_result: ToolResult) -> LLMMessage:
        """Create a tool result message that matches LLM expectations

        For Anthropic: tool results must be content blocks with type "tool_result" containing the output
        For OpenAI: tool results are just "tool" role messages with content
        """
        # For Anthropic, wrap the result in the expected tool_result format
        tool_result_data = {
            "type": "tool_result",
            "tool_use_id": tool_result.tool_call_id,
            "content": tool_result.content
        }
        content = json.dumps(tool_result_data)

        return LLMMessage(
            role="tool",
            content=content
        )
