# Anthropic LLM 工具调用支持实现总结

## 任务概述
为 Anthropic LLM 服务添加工具调用支持，允许 LLM 在与用户对话过程中使用预定义的工具（如搜索、网页内容获取等），增强模型的实时信息获取和处理能力。

## 主要修改
### 文件修改
- `backend/services/anthropic_llm.py` - 更新 LLM 服务以支持工具调用
- `backend/tests/test_anthropic_llm.py` - 添加工具调用功能的完整测试套件

## 实现的功能

### 1. 接受工具定义参数
- 在 `chat_stream` 方法中添加 `tools` 可选参数，类型为 `Optional[List[ToolDefinition]]`
- 默认值为 `None`，保持与现有接口的向后兼容性

### 2. 工具格式转换
- 使用 `ToolDefinition.to_anthropic()` 方法将内部工具定义转换为 Anthropic 格式
- 转换后的格式：
  ```json
  {
    "name": "tool_name",
    "description": "tool description",
    "input_schema": {
      "type": "object",
      "properties": {...},
      "required": [...]
    }
  }
  ```

### 3. 请求参数更新
- 在发送给 Anthropic API 的 JSON 请求中添加 `tools` 字段（当提供工具时）
- 更新 `data` 字典以包含工具信息

### 4. 流式响应解析
- 扩展 `_parse_anthropic_stream` 方法以处理工具调用检测
- 跟踪 `content_block_start` 事件，检查是否为 `tool_use` 类型
- 累积工具输入的部分 JSON 响应
- 在 `content_block_stop` 事件时，将完整的工具调用信息以特殊格式输出

### 5. 工具调用事件格式
- 使用 `[TOOL_CALL]:` 前缀标识工具调用事件
- 事件包含以下信息：
  ```json
  {"type": "tool_call", "id": "tool_use_123", "name": "search", "parameters": {"query": "北京天气"}}
  ```

### 6. 保持兼容性
- 当未提供工具时，保持原有的纯文本流式输出行为
- 只有在存在工具定义时才会发送工具信息和解析工具调用

## 测试覆盖
### 测试用例
- 基础配置检查 (`test_is_configured`)
- 消息转换测试 (`test_convert_message`)
- 无工具调用的对话流测试 (`test_chat_stream_without_tools`)
- 含工具调用的对话流测试 (`test_chat_stream_with_tools`)
- 工具调用解析测试 (`test_parse_anthropic_stream_tool_call`)
- 混合内容解析测试 (`test_parse_anthropic_stream_mixed_content`)

### 测试结果
所有测试均通过：
```
============================= test session starts ==============================
platform darwin -- Python 3.13.12, pytest-9.0.2, pluggy-1.6.0 -- /opt/homebrew/Caskroom/miniforge/base/bin/python
cachedir: .pytest_cache
rootdir: /Users/x1ay/Documents/AIcode/Buddy/backend
plugins: asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items

tests/test_anthropic_llm.py::TestAnthropicLLMService::test_is_configured PASSED [ 16%]
tests/test_anthropic_llm.py::TestAnthropicLLMService::test_convert_message PASSED [ 33%]
tests/test_anthropic_llm.py::TestAnthropicLLMService::test_chat_stream_without_tools PASSED [ 50%]
tests/test_anthropic_llm.py::TestAnthropicLLMService::test_chat_stream_with_tools PASSED [ 66%]
tests/test_anthropic_llm.py::TestAnthropicLLMService::test_parse_anthropic_stream_tool_call PASSED [ 83%]
tests/test_anthropic_llm.py::TestAnthropicLLMService::test_parse_anthropic_stream_mixed_content PASSED [100%]

========================= 6 passed, 1 warning in 0.03s =========================
```

## 代码质量
### 优点
- 保持了与现有代码的一致性和风格
- 添加了充分的注释和文档字符串
- 使用类型提示提高了代码可读性
- 实现了完整的错误处理
- 添加了全面的测试覆盖

### 改进建议
- 可以考虑进一步优化工具调用参数的验证和解析
- 可以添加对工具调用结果返回的支持（作为后续任务）

## 集成说明
该实现与项目中已有的工具调用架构无缝集成，包括：
- `ToolDefinition` 和 `ToolParameter` 类
- `OpenWebSearchClient` HTTP 通信组件
- `ToolExecutor` 工具调度器
- `ToolCall` 和 `ToolResult` 数据模型

## 使用示例

```python
from services.anthropic_llm import AnthropicLLMService
from models.schemas import LLMMessage
from services.tool_calling.tool_definitions import get_tool_definitions

async def main():
    service = AnthropicLLMService()
    
    # 配置工具
    tools = get_tool_definitions()
    
    # 示例对话
    messages = [
        LLMMessage(role="user", content="今天北京的天气如何？")
    ]
    
    async for token in service.chat_stream(messages, tools=tools):
        if token.startswith("[TOOL_CALL]:"):
            # 解析工具调用
            tool_call_json = token.replace("[TOOL_CALL]:", "")
            tool_call = eval(tool_call_json)
            print(f"LLM 正在调用工具: {tool_call['name']}")
            print(f"参数: {tool_call['parameters']}")
        else:
            # 输出文本
            print(token, end="")
```

## 结论
该实现成功地为 Anthropic LLM 服务添加了工具调用支持，提供了完整的功能、全面的测试覆盖和良好的代码质量。LLM 现在可以在对话过程中使用工具获取实时信息，显著增强了其可用性。
