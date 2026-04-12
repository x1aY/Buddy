"""Tests for ToolExecutor class"""
import pytest
from unittest.mock import Mock, AsyncMock
from services.tool_calling.tool_executor import ToolExecutor
from models.schemas import ToolCall
from services.tool_calling.open_websearch_client import OpenWebSearchClient


class TestToolExecutor:
    """Tests for ToolExecutor"""

    @pytest.fixture
    def mock_open_websearch_client(self):
        """Create mock OpenWebSearchClient"""
        mock = Mock(spec=OpenWebSearchClient)
        mock.search = AsyncMock()
        mock.fetch_web_content = AsyncMock()
        mock.fetch_github_readme = AsyncMock()
        mock.fetch_juejin_article = AsyncMock()
        mock.fetch_csdn_article = AsyncMock()
        mock.fetch_linuxdo_article = AsyncMock()
        return mock

    @pytest.fixture
    def tool_executor(self, mock_open_websearch_client):
        """Create ToolExecutor instance with mock client"""
        return ToolExecutor(mock_open_websearch_client)

    @pytest.mark.asyncio
    async def test_execute_known_tool_search_with_correct_parameters_returns_success(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing known tool (search) with correct parameters returns success"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="search",
            parameters={"query": "test query"}
        )

        mock_response = {
            "success": True,
            "result": [{"title": "Test Result", "url": "http://example.com"}]
        }
        mock_open_websearch_client.search.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is True
        assert "Test Result" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.search.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_name_returns_error(self, tool_executor):
        """Test executing unknown tool name returns error"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="unknown_tool",
            parameters={"query": "test query"}
        )

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is False
        assert "Unknown tool" in result.content
        assert result.tool_call_id == "test123"

    @pytest.mark.asyncio
    async def test_execute_search_with_missing_query_parameter_returns_error(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing search with missing 'query' parameter returns error"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="search",
            parameters={"missing": "parameter"}
        )

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is False
        assert "Missing required parameter" in result.content
        assert "query" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_fetch_with_missing_url_parameter_returns_error(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing fetch with missing 'url' parameter returns error"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="fetchWebContent",
            parameters={"missing": "parameter"}
        )

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is False
        assert "Missing required parameter" in result.content
        assert "url" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.fetch_web_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_during_execution_returns_error_properly(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test exception during execution returns error properly"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="search",
            parameters={"query": "test query"}
        )

        mock_open_websearch_client.search.side_effect = Exception("Test exception")

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is False
        assert "Error executing tool" in result.content
        assert "Test exception" in result.content
        assert result.tool_call_id == "test123"

    @pytest.mark.asyncio
    async def test_execute_fetch_github_readme_with_correct_parameters_returns_success(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing fetchGithubReadme with correct parameters returns success"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="fetchGithubReadme",
            parameters={"url": "https://github.com/test/repo"}
        )

        mock_response = {
            "success": True,
            "content": "# Test Repo\nThis is a test README"
        }
        mock_open_websearch_client.fetch_github_readme.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is True
        assert "Test Repo" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.fetch_github_readme.assert_called_once_with(
            "https://github.com/test/repo"
        )

    @pytest.mark.asyncio
    async def test_execute_fetch_juejin_article_with_correct_parameters_returns_success(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing fetchJuejinArticle with correct parameters returns success"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="fetchJuejinArticle",
            parameters={"url": "https://juejin.cn/post/123456"}
        )

        mock_response = {
            "success": True,
            "content": "<h1>Test Article</h1><p>This is a test article</p>"
        }
        mock_open_websearch_client.fetch_juejin_article.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is True
        assert "Test Article" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.fetch_juejin_article.assert_called_once_with(
            "https://juejin.cn/post/123456"
        )

    @pytest.mark.asyncio
    async def test_execute_fetch_csdn_article_with_correct_parameters_returns_success(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing fetchCsdnArticle with correct parameters returns success"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="fetchCsdnArticle",
            parameters={"url": "https://blog.csdn.net/test/article/details/123456"}
        )

        mock_response = {
            "success": True,
            "content": "<h1>Test CSDN Article</h1><p>This is a test CSDN article</p>"
        }
        mock_open_websearch_client.fetch_csdn_article.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is True
        assert "Test CSDN Article" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.fetch_csdn_article.assert_called_once_with(
            "https://blog.csdn.net/test/article/details/123456"
        )

    @pytest.mark.asyncio
    async def test_execute_fetch_linuxdo_article_with_correct_parameters_returns_success(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test executing fetchLinuxDoArticle with correct parameters returns success"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="fetchLinuxDoArticle",
            parameters={"url": "https://linux.do/article/1234"}
        )

        mock_response = {
            "success": True,
            "content": "<h1>Linux.Do Article</h1><p>This is a test Linux.Do article</p>"
        }
        mock_open_websearch_client.fetch_linuxdo_article.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is True
        assert "Linux.Do Article" in result.content
        assert result.tool_call_id == "test123"
        mock_open_websearch_client.fetch_linuxdo_article.assert_called_once_with(
            "https://linux.do/article/1234"
        )

    @pytest.mark.asyncio
    async def test_open_websearch_client_error_response_converted_to_tool_result(
        self, tool_executor, mock_open_websearch_client
    ):
        """Test OpenWebSearchClient error response is converted to tool result"""
        # Arrange
        tool_call = ToolCall(
            id="test123",
            name="search",
            parameters={"query": "test query"}
        )

        mock_response = {
            "success": False,
            "error": "Search API failed",
            "result": []
        }
        mock_open_websearch_client.search.return_value = mock_response

        # Act
        result = await tool_executor.execute(tool_call)

        # Assert
        assert result.success is False
        assert "Search API failed" in result.content
        assert result.tool_call_id == "test123"
