"""工具定义 - 所有 open-websearch 工具的元数据"""
from typing import List, Dict


class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool

    def __init__(self, name: str, type: str, description: str, required: bool = True):
        self.name = name
        self.type = type
        self.description = description
        self.required = required

    def to_anthropic(self) -> dict:
        """转换为 Anthropic 格式"""
        return {
            "type": self.type,
            "description": self.description,
        }

    def to_openai(self) -> dict:
        """转换为 OpenAI 格式"""
        return {
            "type": self.type,
            "description": self.description,
        }


class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter]

    def __init__(self, name: str, description: str, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.parameters = parameters

    def get_required_parameters(self) -> List[str]:
        return [p.name for p in self.parameters if p.required]

    def to_anthropic(self) -> dict:
        """转换为 Anthropic 格式"""
        input_schema = {
            "type": "object",
            "properties": {
                p.name: p.to_anthropic() for p in self.parameters
            },
            "required": self.get_required_parameters(),
        }
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema,
        }

    def to_openai(self) -> dict:
        """转换为 OpenAI 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p.name: p.to_openai() for p in self.parameters
                    },
                    "required": self.get_required_parameters(),
                },
            },
        }


def get_tool_definitions() -> List[ToolDefinition]:
    """获取所有可用工具定义"""
    return [
        ToolDefinition(
            name="search",
            description="搜索网页获取实时信息。用于：当前日期/时间、天气、最近发生的新闻事件、你不确定的事实性问题、需要从互联网获取的最新数据。",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜索关键词"
                )
            ]
        ),
        ToolDefinition(
            name="fetchWebContent",
            description="获取完整网页内容。当搜索结果摘要不够，需要阅读完整文章内容，或用户要求获取某个 URL 的具体内容时使用。",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="要获取的网页 URL"
                )
            ]
        ),
        ToolDefinition(
            name="fetchGithubReadme",
            description="获取 GitHub 仓库的 README 文档。当用户询问某个 GitHub 项目的信息时使用。",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="GitHub 仓库 URL"
                )
            ]
        ),
        ToolDefinition(
            name="fetchJuejinArticle",
            description="获取掘金文章的完整内容。当需要阅读掘金上的技术文章时使用。",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="掘金文章 URL"
                )
            ]
        ),
        ToolDefinition(
            name="fetchCsdnArticle",
            description="获取 CSDN 文章的完整内容。当需要阅读 CSDN 上的技术文章时使用。",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="CSDN 文章 URL"
                )
            ]
        ),
        ToolDefinition(
            name="fetchLinuxDoArticle",
            description="获取 Linux.Do 文章的完整内容。当需要阅读 Linux.Do 上的讨论内容时使用。",
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="Linux.Do 文章 URL"
                )
            ]
        ),
    ]
