"""Tool Executor - Dispatches tool calls to OpenWebSearchClient"""
from dataclasses import dataclass
from typing import Callable, Dict, Any
from models.schemas import ToolCall, ToolResult
from services.tool_calling.open_websearch_client import OpenWebSearchClient
import json


class ToolExecutor:
    """Executes tool calls using OpenWebSearchClient"""

    @dataclass
    class ToolHandler:
        """Metadata for a tool handler"""
        required_param: str
        client_method: Callable[..., Any]

    def __init__(self, open_websearch_client: OpenWebSearchClient):
        """Initialize with OpenWebSearchClient instance"""
        self.open_websearch_client = open_websearch_client
        self._tool_map: Dict[str, ToolExecutor.ToolHandler] = {
            "search": self.ToolHandler("query", open_websearch_client.search),
            "fetchWebContent": self.ToolHandler("url", open_websearch_client.fetch_web_content),
            "fetchGithubReadme": self.ToolHandler("url", open_websearch_client.fetch_github_readme),
            "fetchJuejinArticle": self.ToolHandler("url", open_websearch_client.fetch_juejin_article),
            "fetchCsdnArticle": self.ToolHandler("url", open_websearch_client.fetch_csdn_article),
            "fetchLinuxDoArticle": self.ToolHandler("url", open_websearch_client.fetch_linuxdo_article),
        }

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute tool call and return result

        Args:
            tool_call: ToolCall object containing tool name and parameters

        Returns:
            ToolResult object with execution result
        """
        try:
            # Get handler for tool name
            handler = self._tool_map.get(tool_call.name)
            if not handler:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=f"Unknown tool: {tool_call.name}",
                    success=False
                )

            # Check required parameter
            param_value = tool_call.parameters.get(handler.required_param)
            if not param_value:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    content=f"Missing required parameter: '{handler.required_param}'",
                    success=False
                )

            # Execute client method and convert result
            response = await handler.client_method(param_value)
            return self._convert_response(response, tool_call.id)

        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error executing tool '{tool_call.name}': {str(e)}",
                success=False
            )

    def _convert_response(self, response: dict, tool_call_id: str) -> ToolResult:
        """Convert OpenWebSearchClient response to ToolResult"""
        if response.get("success"):
            # For search tool, response has "result" field; others have "content"
            if "result" in response:
                content = json.dumps(response["result"])
            elif "content" in response:
                content = response["content"]
            else:
                content = json.dumps(response)
            return ToolResult(
                tool_call_id=tool_call_id,
                content=content,
                success=True
            )
        else:
            return ToolResult(
                tool_call_id=tool_call_id,
                content=response.get("error", "Unknown error"),
                success=False
            )
