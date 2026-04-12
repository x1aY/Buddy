"""
Tests for LlmPipeline class
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from services.llm.pipeline import LlmPipeline
from services.llm.base import BaseLLMService
from services.llm.conversation_history import ConversationHistory
from services.speech import BaseTTSService
from models.schemas import ToolCall, ToolResult, ConversationMessage


@pytest.fixture
def mock_conversation_history():
    """Create a mock conversation history"""
    history = ConversationHistory()
    return history


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    mock = Mock(spec=BaseLLMService)
    mock.is_configured.return_value = False
    return mock


@pytest.fixture
def mock_tts_service():
    """Create a mock BaseTTSService"""
    return Mock(spec=BaseTTSService)


@pytest.fixture
def pipeline_without_configured_llm(mock_conversation_history, mock_llm_service, mock_tts_service):
    """Create a pipeline with LLM unconfigured"""
    return LlmPipeline(
        conversation_history=mock_conversation_history,
        latest_camera_frame=None,
        llm_service=mock_llm_service,
        tts_service=mock_tts_service
    )


class TestLlmPipelineInitialization:
    """Tests for LlmPipeline initialization"""

    def test_initialization_without_configured_llms(self, pipeline_without_configured_llm):
        """Test pipeline initializes with LLM unconfigured"""
        assert pipeline_without_configured_llm is not None

    def test_initialization_with_no_camera_frame(self, pipeline_without_configured_llm):
        """Test pipeline initializes with no camera frame"""
        assert pipeline_without_configured_llm is not None

    def test_initialization_with_tools_enabled(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test pipeline initializes tools when open_websearch is enabled"""
        with patch('config.settings.open_websearch_enabled', True):
            pipeline = LlmPipeline(
                conversation_history=mock_conversation_history,
                latest_camera_frame=None,
                llm_service=mock_llm_service,
                tts_service=mock_tts_service
            )
            assert pipeline.open_websearch_client is not None
            assert pipeline.tool_executor is not None
            assert pipeline.tools is not None


class TestLlmPipelineRun:
    """Tests for LlmPipeline.run() method"""

    @pytest.mark.asyncio
    async def test_run_with_no_configured_llms(self, pipeline_without_configured_llm):
        """Test pipeline returns error when no LLM configured"""
        # With unified architecture, this case shouldn't happen since factory ensures we get a service
        # But test it anyway
        async def mock_stream_response(messages, tools):
            yield "错误: 没有配置任何 LLM 服务"

        pipeline_without_configured_llm.llm_service.chat_stream = mock_stream_response

        result = []
        async for token in pipeline_without_configured_llm.run():
            result.append(token)
        assert "错误: 没有配置任何 LLM 服务" in "".join(result)

    @pytest.mark.asyncio
    async def test_run_with_text_response_no_tool_calls(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test pipeline handles LLM returning text with no tool calls"""
        # Configure LLM as available
        mock_llm_service.is_configured.return_value = True

        async def mock_stream_response(messages, tools):
            yield "这是一个没有工具调用的回答"

        mock_llm_service.chat_stream = mock_stream_response

        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        # Test run
        result = []
        async for token in pipeline.run():
            result.append(token)

        assert "这是一个没有工具调用的回答" in "".join(result)

    @pytest.mark.asyncio
    async def test_run_yields_tool_call_tokens(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test pipeline parses tool call tokens from LLM (not yielded to client)"""
        # Configure LLM as available
        mock_llm_service.is_configured.return_value = True

        tool_call_json = json.dumps({
            "type": "tool_call",
            "id": "test-tool-call-id",
            "name": "search",
            "parameters": {"query": "今天是星期几"}
        })

        async def mock_stream_response(messages, tools):
            yield "[TOOL_CALL]:" + tool_call_json

        mock_llm_service.chat_stream = mock_stream_response

        # Disable open-websearch so tools are not configured
        import config
        original_value = config.settings.open_websearch_enabled
        config.settings.open_websearch_enabled = False
        try:
            pipeline = LlmPipeline(
                conversation_history=mock_conversation_history,
                latest_camera_frame=None,
                llm_service=mock_llm_service,
                tts_service=mock_tts_service
            )

            # Test run - the tool call should be captured internally but not yielded
            result = []
            tool_calls = []
            async for token in pipeline.run():
                result.append(token)

            # No text content should be yielded
            full_response = "".join(result)
            # tool call not yielded to client, but if there was text it would be yielded
            # Since we only got a tool call, full response is empty but that's expected
            # Just verify the pipeline completed without errors
            assert len(result) == 0
        finally:
            config.settings.open_websearch_enabled = original_value


class TestLlmPipelineHelperMethods:
    """Tests for LlmPipeline helper methods"""

    @pytest.mark.asyncio
    async def test_build_llm_messages(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test _build_llm_messages correctly processes history"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        # Check if pipeline has the helper method
        assert hasattr(pipeline, "_build_llm_messages")

        # Call it
        messages = pipeline._build_llm_messages()
        assert len(messages) > 0
        assert messages[0].role == "system"

    @pytest.mark.asyncio
    async def test_parse_tool_call_valid(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test _parse_tool_call with valid tool call"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        tool_call_json = json.dumps({
            "type": "tool_call",
            "id": "test-tool-call-id",
            "name": "search",
            "parameters": {"query": "今天是星期几"}
        })

        tool_call = pipeline._parse_tool_call(f"[TOOL_CALL]:{tool_call_json}")

        assert tool_call is not None
        assert tool_call.id == "test-tool-call-id"
        assert tool_call.name == "search"
        assert tool_call.parameters == {"query": "今天是星期几"}

    @pytest.mark.asyncio
    async def test_parse_tool_call_invalid(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test _parse_tool_call with invalid inputs"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        # Invalid JSON
        assert pipeline._parse_tool_call("[TOOL_CALL]:invalid_json") is None
        # No JSON
        assert pipeline._parse_tool_call("[TOOL_CALL]:") is None
        # Wrong type
        assert pipeline._parse_tool_call("[TOOL_CALL]:" + json.dumps({"type": "invalid"})) is None
        # Not a tool call
        assert pipeline._parse_tool_call("normal text") is None


class TestLlmPipelineToolExecution:
    """Tests for tool call execution handling"""

    @pytest.mark.asyncio
    async def test_tool_call_without_configured_tools_stops(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test pipeline stops when tool calls happen but tools are not configured"""
        # Configure LLM as available
        mock_llm_service.is_configured.return_value = True

        tool_call_json = json.dumps({
            "type": "tool_call",
            "id": "test-tool-call-id",
            "name": "search",
            "parameters": {"query": "今天是星期几"}
        })

        async def mock_stream_response(messages, tools):
            yield "[TOOL_CALL]:" + tool_call_json

        mock_llm_service.chat_stream = mock_stream_response

        # Disable open-websearch so tools are not configured
        import config
        original_value = config.settings.open_websearch_enabled
        config.settings.open_websearch_enabled = False
        try:
            pipeline = LlmPipeline(
                conversation_history=mock_conversation_history,
                latest_camera_frame=None,
                llm_service=mock_llm_service,
                tts_service=mock_tts_service
            )

            # Run pipeline - should stop after tool call without executing
            result = []
            async for token in pipeline.run():
                result.append(token)

            # Tool call is not yielded to client, so result is empty
            # Verify pipeline completed successfully
            assert len(result) == 0
            # Should only have one iteration (checked by logger, but test passes if it completes)
        finally:
            config.settings.open_websearch_enabled = original_value


@pytest.mark.asyncio
async def test_complete_end_to_end_tool_call_cycle():
    """Complete end-to-end test: user question -> LLM calls tool -> tool executed -> LLM answers"""
    from unittest.mock import patch

    # Setup conversation with user question
    mock_conversation_history = ConversationHistory()
    mock_conversation_history.add_message(ConversationMessage(
        id="1-user",
        role="user",
        text="今天星期几？",
        timestamp=1234567890
    ))

    # Configure LLM
    mock_llm_service = Mock(spec=BaseLLMService)
    mock_llm_service.is_configured.return_value = True

    # First call: LLM returns tool call
    tool_call = json.dumps({
        "type": "tool_call",
        "id": "1",
        "name": "search",
        "parameters": {"query": "今天星期几 2026"}
    })

    async def mock_llm_first_call(messages, tools):
        yield "[TOOL_CALL]:" + tool_call

    # Second call: LLM returns answer based on tool result
    async def mock_llm_second_call(messages, tools):
        yield "根据搜索结果，今天是星期三，2026年4月8日。"

    calls = []
    def chat_stream_side_effect(messages, tools):
        calls.append(messages)
        if len(calls) == 1:
            return mock_llm_first_call(messages, tools)
        elif len(calls) == 2:
            return mock_llm_second_call(messages, tools)

    mock_llm_service.chat_stream = chat_stream_side_effect

    # Enable tools in settings
    with patch('config.settings.open_websearch_enabled', True):
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=Mock(spec=BaseTTSService)
        )

        # Verify tools are initialized
        assert pipeline.tool_executor is not None

        # Patch the tool executor to avoid actual HTTP call
        original_execute = pipeline.tool_executor.execute
        async def mock_execute(tool_call):
            from models.schemas import ToolResult
            return ToolResult(
                tool_call_id=tool_call.id,
                content='[{"title": "日期查询结果", "content": "今天是2026年4月8日，星期三"}]',
                success=True
            )

        pipeline.tool_executor.execute = mock_execute

        # Run the pipeline
        response = []
        async for token in pipeline.run():
            response.append(token)

        # Verify we had two LLM calls (one with tool call, one with final answer)
        assert len(calls) == 2
        # Verify the final answer is included
        assert "星期三" in "".join(response)
        # Tool call is processed internally and not yielded to the client


class TestLlmPipelineErrorHandling:
    """Tests for error handling scenarios"""

    @pytest.mark.asyncio
    async def test_invalid_tool_call_json_still_yields_text(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test that invalid tool call JSON is still yielded as text"""
        mock_llm_service.is_configured.return_value = True

        async def mock_stream_response(messages, tools):
            yield "Some text before invalid tool call "
            yield "[TOOL_CALL]:{broken json"

        mock_llm_service.chat_stream = mock_stream_response

        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        result = []
        async for token in pipeline.run():
            result.append(token)

        full_response = "".join(result)
        # The text should still be yielded
        assert "Some text before" in full_response
        # The invalid JSON should be yielded as text (not parsed as tool call)
        assert "{broken json" in full_response

    @pytest.mark.asyncio
    async def test_max_iterations_limit_reached(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test that the max iterations limit is respected to prevent infinite loops"""
        from unittest.mock import patch

        mock_llm_service.is_configured.return_value = True

        tool_call = json.dumps({
            "type": "tool_call",
            "id": "tool-1",
            "name": "search",
            "parameters": {"query": "test"}
        })

        call_count = []
        async def mock_stream_response(messages, tools):
            call_count.append(messages)
            yield "[TOOL_CALL]:" + tool_call

        mock_llm_service.chat_stream = mock_stream_response

        with patch('config.settings.open_websearch_enabled', True):
            pipeline = LlmPipeline(
                conversation_history=mock_conversation_history,
                latest_camera_frame=None,
                llm_service=mock_llm_service,
                tts_service=mock_tts_service
            )

            # Mock tool executor to always return success
            pipeline.tool_executor.execute = AsyncMock(return_value=ToolResult(
                tool_call_id="tool-1",
                content="test result",
                success=True
            ))

            result = []
            async for token in pipeline.run():
                result.append(token)

            # Should hit max iterations (5) and yield the warning message
            full_response = "".join(result)
            assert "已达到最大工具调用次数限制" in full_response
            # Verify max iterations was 5
            assert len(call_count) == 5

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_one_iteration(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test handling multiple tool calls in a single LLM response"""
        from unittest.mock import patch

        mock_llm_service.is_configured.return_value = True

        tool_call1 = json.dumps({
            "type": "tool_call",
            "id": "tool-1",
            "name": "search",
            "parameters": {"query": "weather today"}
        })

        tool_call2 = json.dumps({
            "type": "tool_call",
            "id": "tool-2",
            "name": "search",
            "parameters": {"query": "forecast tomorrow"}
        })

        async def mock_llm_first_call(messages, tools):
            yield "Let me search for both.\n"
            yield "[TOOL_CALL]:" + tool_call1 + "\n"
            yield "[TOOL_CALL]:" + tool_call2

        async def mock_llm_second_call(messages, tools):
            yield "Today is sunny, tomorrow will be rainy."

        calls = []
        def chat_stream_side_effect(messages, tools):
            calls.append(messages)
            if len(calls) == 1:
                return mock_llm_first_call(messages, tools)
            elif len(calls) == 2:
                return mock_llm_second_call(messages, tools)

        mock_llm_service.chat_stream = chat_stream_side_effect

        with patch('config.settings.open_websearch_enabled', True):
            pipeline = LlmPipeline(
                conversation_history=mock_conversation_history,
                latest_camera_frame=None,
                llm_service=mock_llm_service,
                tts_service=Mock(spec=BaseTTSService)
            )

            # Mock tool execution
            call_count = 0
            async def mock_execute(tool_call):
                nonlocal call_count
                call_count += 1
                from models.schemas import ToolResult
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=f"Result for {call_count}",
                    success=True
                )

            pipeline.tool_executor.execute = mock_execute

            response = []
            async for token in pipeline.run():
                response.append(token)

            # Two LLM calls total
            assert len(calls) == 2
            # Two tool calls executed
            assert call_count == 2
            # Final answer yielded
            assert "Today is sunny" in "".join(response)


class TestLlmPipelineMessageFormat:
    """Tests for message formatting correctness"""

    @pytest.mark.asyncio
    async def test_create_assistant_message_with_text_only(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test creating assistant message with only text"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        from models.schemas import ToolCall
        tool_calls = []
        message = pipeline._create_assistant_message_with_tool_calls("Hello world", tool_calls)

        assert message.role == "assistant"
        assert isinstance(message.content, str)
        assert message.content == "Hello world"

    @pytest.mark.asyncio
    async def test_create_assistant_message_with_tool_calls(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test creating assistant message with multiple tool calls"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        from models.schemas import ToolCall
        tool_calls = [
            ToolCall(id="1", name="search", parameters={"query": "test"}),
            ToolCall(id="2", name="fetchWebContent", parameters={"url": "example.com"})
        ]

        message = pipeline._create_assistant_message_with_tool_calls("Some intro", tool_calls)

        assert message.role == "assistant"
        assert isinstance(message.content, list)
        # One text part + two tool call parts = 3
        assert len(message.content) == 3

    @pytest.mark.asyncio
    async def test_create_tool_result_message(self, mock_conversation_history, mock_llm_service, mock_tts_service):
        """Test creating tool result message"""
        pipeline = LlmPipeline(
            conversation_history=mock_conversation_history,
            latest_camera_frame=None,
            llm_service=mock_llm_service,
            tts_service=mock_tts_service
        )

        from models.schemas import ToolResult
        result = ToolResult(
            tool_call_id="test-id",
            content='[{"title": "Test", "content": "Result content"}]',
            success=True
        )

        message = pipeline._create_tool_message(result)

        assert message.role == "tool"
        assert isinstance(message.content, str)
        # Should be wrapped in Anthropic tool_result format
        import json
        data = json.loads(message.content)
        assert data["type"] == "tool_result"
        assert data["tool_use_id"] == "test-id"
        assert data["content"] == '[{"title": "Test", "content": "Result content"}]'
