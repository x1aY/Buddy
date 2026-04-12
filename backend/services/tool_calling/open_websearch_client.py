"""OpenWebSearch HTTP client - Async HTTP client for open-websearch MCP daemon"""
import httpx
from typing import Dict, List, Optional, Any
from config import Settings


class OpenWebSearchClient:
    """Async HTTP client for interacting with open-websearch daemon

    This client provides methods to:
    - Check if the service is configured and healthy
    - Search the web
    - Fetch full web content from various sources (general web, GitHub, Juejin, CSDN, Linux.Do)
    """

    def __init__(self, settings: Settings):
        """Initialize client from settings"""
        self.enabled = settings.open_websearch_enabled
        self.base_url = settings.open_websearch_base_url.rstrip('/')
        self.timeout = settings.open_websearch_timeout
        # Disable proxy explicitly for localhost connections to avoid 502 errors from system proxies
        # proxy=None completely disables proxy usage in httpx
        self.client = httpx.AsyncClient(timeout=self.timeout, proxy=None)

    def is_configured(self) -> bool:
        """Check if open-websearch is enabled and configured

        Returns:
            bool: True if enabled, False otherwise
        """
        return self.enabled

    async def health_check(self) -> Dict[str, Any]:
        """Check if the open-websearch daemon is running

        Returns:
            dict: {"success": bool, "error": str}
        """
        try:
            url = f"{self.base_url}/health"
            response = await self.client.get(url)
            if response.status_code == 200:
                return {
                    "success": True,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "error": f"Health check failed with status {response.status_code}: {response.text}"
                }
        except httpx.TimeoutException as e:
            return {
                "success": False,
                "error": f"Request timed out: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }

    async def search(self, query: str) -> Dict[str, Any]:
        """Search the web for the given query

        Args:
            query: Search query string

        Returns:
            dict: {"success": bool, "result": list[dict], "error": str}
        """
        try:
            url = f"{self.base_url}/search"
            payload = {"query": query}

            response = await self.client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    results = data
                elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], dict) and 'results' in data['data']:
                    # open-websearch daemon format: { "status": "ok", "data": { "results": [...] } }
                    results = data['data']['results'] if isinstance(data['data']['results'], list) else []
                elif isinstance(data, dict) and 'results' in data:
                    # Alternative format: { "results": [...] }
                    results = data['results'] if isinstance(data['results'], list) else []
                else:
                    results = []
                return {
                    "success": True,
                    "result": results,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "result": [],
                    "error": f"Search failed with status {response.status_code}: {response.text}"
                }
        except httpx.TimeoutException as e:
            return {
                "success": False,
                "result": [],
                "error": f"Request timed out: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "result": [],
                "error": f"Search request failed: {str(e)}"
            }

    async def _fetch_url(self, endpoint_path: str, url: str) -> Dict[str, Any]:
        """Internal helper method to fetch content from a URL endpoint

        Args:
            endpoint_path: Endpoint path without base URL
            url: URL to fetch content from

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        try:
            endpoint = f"{self.base_url}/{endpoint_path.lstrip('/')}"
            payload = {"url": url}

            response = await self.client.post(endpoint, json=payload)

            if response.status_code == 200:
                # Response format: { "status": "ok", "data": { "content": "..." } }
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data and isinstance(data['data'], dict):
                        content = data['data'].get('content', response.text)
                    else:
                        content = response.text
                except Exception:
                    # If not JSON, return raw text
                    content = response.text
                return {
                    "success": True,
                    "content": content,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "content": "",
                    "error": f"Fetch failed with status {response.status_code}: {response.text}"
                }
        except httpx.TimeoutException as e:
            return {
                "success": False,
                "content": "",
                "error": f"Request timed out: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": f"Fetch request failed: {str(e)}"
            }

    async def fetch_web_content(self, url: str) -> Dict[str, Any]:
        """Fetch full web page content from a URL

        Args:
            url: Web page URL to fetch

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        return await self._fetch_url("fetch-web", url)

    async def fetch_github_readme(self, url: str) -> Dict[str, Any]:
        """Fetch GitHub repository README content

        Args:
            url: GitHub repository URL

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        return await self._fetch_url("fetch-github-readme", url)

    async def fetch_juejin_article(self, url: str) -> Dict[str, Any]:
        """Fetch Juejin article content

        Args:
            url: Juejin article URL

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        return await self._fetch_url("fetch-juejin", url)

    async def fetch_csdn_article(self, url: str) -> Dict[str, Any]:
        """Fetch CSDN article content

        Args:
            url: CSDN article URL

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        return await self._fetch_url("fetch-csdn", url)

    async def fetch_linuxdo_article(self, url: str) -> Dict[str, Any]:
        """Fetch Linux.Do article content

        Args:
            url: Linux.Do article URL

        Returns:
            dict: {"success": bool, "content": str, "error": str}
        """
        return await self._fetch_url("fetch-linuxdo", url)
