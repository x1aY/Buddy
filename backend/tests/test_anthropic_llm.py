"""
Tests for Anthropic LLM Service with tool calling support
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from services.llm.providers.anthropic import AnthropicLLMService
from models.schemas import LLMMessage
from services.tool_calling.tool_definitions import ToolDefinition, ToolParameter


@pytest.fixture
def anthropic_service():
    """Create an AnthropicLLMService instance for testing"""
    service = AnthropicLLMService()
    # Mock the settings
    service.auth_token = "test-token"
    service.base_url = "https://api.anthropic.com"
    service.model = "claude-3-opus-20240229"
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


class TestAnthropicLLMService:
    """Tests for AnthropicLLMService"""

    def test_is_configured(self, anthropic_service):
        """Test is_configured method"""
        assert anthropic_service.is_configured() is True

        anthropic_service.auth_token = ""
        assert anthropic_service.is_configured() is False

        anthropic_service.auth_token = None
        assert anthropic_service.is_configured() is False

    def test_convert_message(self, anthropic_service):
        """Test _convert_message method"""
        # Test text message
        msg = LLMMessage(role="user", content="Hello")
        result = anthropic_service._convert_message(msg)
        assert result == {"role": "user", "content": "Hello"}

        # Test assistant role
        msg = LLMMessage(role="assistant", content="Hi there")
        result = anthropic_service._convert_message(msg)
        assert result == {"role": "assistant", "content": "Hi there"}

    @pytest.mark.asyncio
    async def test_chat_stream_without_tools(self, anthropic_service, sample_messages):
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
            async for token in anthropic_service.chat_stream(sample_messages):
                tokens.append(token)

            # Verify text tokens were received
            assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_chat_stream_with_tools(self, anthropic_service, sample_messages, sample_tools):
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
            async for _ in anthropic_service.chat_stream(sample_messages, tools=sample_tools):
                pass

            # Verify tools were included in the request
            assert captured_data is not None
            assert "tools" in captured_data
            assert len(captured_data["tools"]) == 1
            assert captured_data["tools"][0]["name"] == "search"

    @pytest.mark.asyncio
    async def test_parse_anthropic_stream_tool_call(self, anthropic_service):
        """Test parsing tool call from stream"""
        mock_response = AsyncMock()
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_tool_stream())

        tokens = []
        async for token in anthropic_service._parse_anthropic_stream(mock_response):
            tokens.append(token)

        # Should have one tool call event
        tool_call_tokens = [t for t in tokens if t.startswith("[TOOL_CALL]:")]
        assert len(tool_call_tokens) == 1

        # Parse the tool call
        tool_call_json = tool_call_tokens[0].replace("[TOOL_CALL]:", "")
        tool_call = json.loads(tool_call_json)
        from services.llm.providers.anthropic import TOOL_CALL_EVENT_TYPE
        assert tool_call["type"] == TOOL_CALL_EVENT_TYPE
        assert tool_call["id"] == "tool_use_123"
        assert tool_call["name"] == "search"
        assert tool_call["parameters"] == {"query": "test search"}

    @pytest.mark.asyncio
    async def test_parse_anthropic_stream_mixed_content(self, anthropic_service):
        """Test parsing stream with both text and tool calls"""
        mock_response = AsyncMock()
        mock_response.aiter_lines = MagicMock(return_value=self._create_mock_mixed_stream())

        tokens = []
        async for token in anthropic_service._parse_anthropic_stream(mock_response):
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
            "event: content_block_start",
            'data: {"content_block": {"type": "text", "text": ""}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "text_delta", "text": "Hello"}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "text_delta", "text": " world"}}',
            "",
            "event: content_block_stop",
            'data: {}',
            "",
            "event: message_stop",
            'data: {}',
        ]
        return self._async_generator(lines)

    def _create_mock_tool_stream(self):
        """Create a mock tool call stream response"""
        lines = [
            "event: content_block_start",
            'data: {"content_block": {"type": "tool_use", "id": "tool_use_123", "name": "search", "input": {}}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "input_json_delta", "partial_json": "{\\"query\\": \\"test search\\"}"}}',
            "",
            "event: content_block_stop",
            'data: {}',
            "",
            "event: message_stop",
            'data: {}',
        ]
        return self._async_generator(lines)

    def _create_mock_mixed_stream(self):
        """Create a mock stream with both text and tool calls"""
        lines = [
            "event: content_block_start",
            'data: {"content_block": {"type": "text", "text": ""}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "text_delta", "text": "Let me"}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "text_delta", "text": " search for that."}}',
            "",
            "event: content_block_stop",
            'data: {}',
            "",
            "event: content_block_start",
            'data: {"content_block": {"type": "tool_use", "id": "tool_use_456", "name": "search", "input": {}}}',
            "",
            "event: content_block_delta",
            'data: {"delta": {"type": "input_json_delta", "partial_json": "{\\"query\\": \\"information\\"}"}}',
            "",
            "event: content_block_stop",
            'data: {}',
            "",
            "event: message_stop",
            'data: {}',
        ]
        return self._async_generator(lines)

    async def _async_generator(self, items):
        """Helper to create async generator from sync list"""
        for item in items:
            yield item
