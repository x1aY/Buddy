"""Unit tests for OpenWebSearchClient"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from services.tool_calling.open_websearch_client import OpenWebSearchClient
from config import settings


class TestOpenWebSearchClient:
    """测试 OpenWebSearchClient 的单元测试"""

    def test_is_configured_when_enabled(self):
        """当 open_websearch_enabled 为 True 时，is_configured 应该返回 True"""
        with patch('config.settings.open_websearch_enabled', True):
            client = OpenWebSearchClient(settings)
            assert client.is_configured() is True

    def test_is_configured_when_disabled(self):
        """当 open_websearch_enabled 为 False 时，is_configured 应该返回 False"""
        with patch('config.settings.open_websearch_enabled', False):
            client = OpenWebSearchClient(settings)
            assert client.is_configured() is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """当 daemon 正常响应时，health_check 应该返回 success: True"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.health_check()
            assert result['success'] is True
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self):
        """当 daemon 无法连接时，health_check 应该返回 success: False 和错误信息"""

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.health_check()
            assert result['success'] is False
            assert "Connection" in result['error']

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """当请求超时时，health_check 应该返回 success: False 和错误信息"""

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.health_check()
            assert result['success'] is False
            assert "Timeout" in result['error']

    @pytest.mark.asyncio
    async def test_health_check_500_error(self):
        """当 daemon 返回 500 错误时，health_check 应该返回 success: False"""

        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.health_check()
            assert result['success'] is False
            assert "500" in result['error']

    @pytest.mark.asyncio
    async def test_search_success(self):
        """搜索成功时应该返回结果列表"""

        mock_results = [
            {
                "title": "Test Result",
                "url": "https://example.com",
                "snippet": "This is a test result"
            }
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_results

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.search("test query")
            assert result['success'] is True
            assert len(result['result']) == 1
            assert result['result'][0]['title'] == "Test Result"
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_search_timeout(self):
        """搜索超时时应该正确处理并返回错误"""

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.search("test query")
            assert result['success'] is False
            assert "time" in result['error'].lower()

    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """搜索网络错误时应该正确处理并返回错误"""

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.search("test query")
            assert result['success'] is False
            assert "Connection" in result['error']

    @pytest.mark.asyncio
    async def test_fetch_web_content_success(self):
        """获取网页内容成功时返回内容"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>This is the web content</body></html>"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_web_content("https://example.com")
            assert result['success'] is True
            assert "This is the web content" in result['content']
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_fetch_web_content_network_error(self):
        """获取网页内容网络错误时正确处理错误"""

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Failed to connect"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_web_content("https://example.com")
            assert result['success'] is False
            assert result['content'] == ''
            assert "Failed" in result['error']

    @pytest.mark.asyncio
    async def test_fetch_github_readme_success(self):
        """获取 GitHub README 成功时返回内容"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "# Test Project\n\nThis is a test project."

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_github_readme("https://github.com/example/test")
            assert result['success'] is True
            assert "# Test Project" in result['content']
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_fetch_juejin_article_success(self):
        """获取掘金文章成功时返回内容"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "This is the article content"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_juejin_article("https://juejin.cn/post/12345")
            assert result['success'] is True
            assert "article content" in result['content']
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_fetch_csdn_article_success(self):
        """获取 CSDN 文章成功时返回内容"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "CSDN article content"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_csdn_article("https://blog.csdn.net/user/article/12345")
            assert result['success'] is True
            assert "CSDN article" in result['content']
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_fetch_linuxdo_article_success(self):
        """获取 Linux.Do 文章成功时返回内容"""

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "Linux.Do discussion content"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_linuxdo_article("https://linux.do/t/topic/12345")
            assert result['success'] is True
            assert "Linux.Do" in result['content']
            assert result['error'] == ''

    @pytest.mark.asyncio
    async def test_all_fetch_methods_handle_timeout(self):
        """所有 fetch 方法都应该正确处理超时"""

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            # Test fetch_web_content
            result1 = await client.fetch_web_content("https://example.com")
            assert result1['success'] is False
            assert "Timeout" in result1['error']

            # Test fetch_github_readme
            result2 = await client.fetch_github_readme("https://github.com/example/test")
            assert result2['success'] is False
            assert "Timeout" in result2['error']

            # Test fetch_juejin_article
            result3 = await client.fetch_juejin_article("https://juejin.cn/post/12345")
            assert result3['success'] is False
            assert "Timeout" in result3['error']

            # Test fetch_csdn_article
            result4 = await client.fetch_csdn_article("https://blog.csdn.net/user/article/12345")
            assert result4['success'] is False
            assert "Timeout" in result4['error']

            # Test fetch_linuxdo_article
            result5 = await client.fetch_linuxdo_article("https://linux.do/t/topic/12345")
            assert result5['success'] is False
            assert "Timeout" in result5['error']

    @pytest.mark.asyncio
    async def test_all_fetch_methods_handle_http_error(self):
        """所有 fetch 方法都应该正确处理 HTTP 错误"""

        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_client):
            client = OpenWebSearchClient(settings)
            result = await client.fetch_web_content("https://example.com/nonexistent")
            assert result['success'] is False
            assert "404" in result['error']
            assert "Not Found" in result['error']
