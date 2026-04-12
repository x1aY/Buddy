"""
Tests for OpenAI LLM Service with tool calling support
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from services.llm.providers.openai import OpenAILLMService
from models.schemas import LLMMessage
from services.tool_calling.tool_definitions import ToolDefinition, ToolParameter


@pytest.fixture
def openai_service():
    """Create an OpenAILLMService instance for testing"""
    service = OpenAILLMService()
    # Mock the settings
    service.api_key = "test-key"
    service.base_url = "https://api.openai.com"
    service.model = "gpt-4o"
    return service


@pytest.fixture
def sample_tools():
    """Create sample tool definitions for testing"""
    return [
        ToolDefinition(
            name="search",
            description="Search the web",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query")
            ]
        )
    ]


@pytest.fixture
def sample_messages():
    """Create sample messages for testing"""
    return [
        LLMMessage(role="user", content="Hello, how are you?")
    ]


class TestOpenAILLMService:
    """Tests for OpenAILLMService"""

    def test_is_configured(self, openai_service):
        """Test is_configured method"""
        assert openai_service.is_configured() is True

        openai_service.api_key = ""
        assert openai_service.is_configured() is False

        openai_service.api_key = None
        assert openai_service.is_configured() is False

    @pytest.mark.asyncio
    async def test_chat_stream_without_tools(self, openai_service, sample_messages):
        """Test chat_stream without tools (backward compatibility)"""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 200

        # Create an async generator for the lines
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_text_stream())

        # Create a context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response

        with patch('httpx.AsyncClient.stream', return_value=mock_stream_cm):
            tokens = []
            async for token in openai_service.chat_stream(sample_messages):
                tokens.append(token)

            # Verify text tokens were received
            assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_chat_stream_with_tools(self, openai_service, sample_messages, sample_tools):
        """Test chat_stream with tools parameter"""
        # Verify tools are included in the request
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_text_stream())

        # Create a context manager mock
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response

        captured_data = None
        def mock_stream(method, url, headers, json):
            nonlocal captured_data
            captured_data = json
            return mock_stream_cm

        with patch('httpx.AsyncClient.stream', side_effect=mock_stream):
            async for _ in openai_service.chat_stream(sample_messages, tools=sample_tools):
                pass

            # Verify tools were included in the request
            assert captured_data is not None
            assert "tools" in captured_data
            assert len(captured_data["tools"]) == 1
            assert captured_data["tools"][0]["type"] == "function"
            assert captured_data["tools"][0]["function"]["name"] == "search"

    @pytest.mark.asyncio
    async def test_parse_openai_stream_tool_call(self, openai_service):
        """Test parsing tool call from stream"""
        # We need to test the parse_openai_stream function directly
        from utils.openai_stream import parse_openai_stream

        mock_response = AsyncMock()
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_tool_stream())

        tokens = []
        async for token in parse_openai_stream(mock_response):
            tokens.append(token)

        # Should have one tool call event
        tool_call_tokens = [t for t in tokens if t.startswith("[TOOL_CALL]:")]
        assert len(tool_call_tokens) == 1

        # Parse the tool call
        tool_call_json = tool_call_tokens[0].replace("[TOOL_CALL]:", "")
        tool_call = json.loads(tool_call_json)
        assert tool_call["type"] == "tool_call"
        assert tool_call["id"] == "call_abc123"
        assert tool_call["name"] == "search"
        assert tool_call["parameters"] == {"query": "test search"}

    @pytest.mark.asyncio
    async def test_parse_openai_stream_mixed_content(self, openai_service):
        """Test parsing stream with both text and tool calls"""
        from utils.openai_stream import parse_openai_stream

        mock_response = AsyncMock()
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_mixed_stream())

        tokens = []
        async for token in parse_openai_stream(mock_response):
            tokens.append(token)

        # Separate text and tool call tokens
        text_tokens = [t for t in tokens if not t.startswith("[TOOL_CALL]:")]
        tool_call_tokens = [t for t in tokens if t.startswith("[TOOL_CALL]:")]

        # Verify text content
        assert "".join(text_tokens) == "Let me search for that."

        # Verify tool call
        assert len(tool_call_tokens) == 1
        tool_call_json = tool_call_tokens[0].replace("[TOOL_CALL]:", "")
        tool_call = json.loads(tool_call_json)
        assert tool_call["name"] == "search"

    def _create_mock_text_stream(self):
        """Create a mock text stream response"""
        lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {"content": " world"}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}]}',
            '',
            'data: [DONE]'
        ]
        return self._async_generator(lines)

    def _create_mock_tool_stream(self):
        """Create a mock tool call stream response"""
        lines = [
            'data: {"choices": [{"delta": {"tool_calls": [{"id": "call_abc123", "function": {"name": "search", "arguments": "{\\"query\\": \\"test search\\"}"}, "type": "function"}]}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {}, "index": 0, "finish_reason": "tool_calls"}]}',
            '',
            'data: [DONE]'
        ]
        return self._async_generator(lines)

    def _create_mock_mixed_stream(self):
        """Create a mock stream with both text and tool calls"""
        lines = [
            'data: {"choices": [{"delta": {"content": "Let me"}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {"content": " search for that."}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {"tool_calls": [{"id": "call_abc123", "function": {"name": "search", "arguments": "{\\"query\\": \\"information\\"}"}, "type": "function"}]}, "index": 0, "finish_reason": null}]}',
            '',
            'data: {"choices": [{"delta": {}, "index": 0, "finish_reason": "tool_calls"}]}',
            '',
            'data: [DONE]'
        ]
        return self._async_generator(lines)

    async def _async_generator(self, items):
        """Helper to create async generator from sync list"""
        for item in items:
            yield item
