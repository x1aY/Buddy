# Open-WebSearch MCP 集成设计文档

## 项目背景
当前后端无法回答需要实时信息的常识性问题，例如"今天是星期几"、"现在几点钟"。需要集成 open-websearch MCP 服务，让 LLM 在遇到不清楚的问题时可以自主搜索网页，然后基于搜索结果回答。

同时，原 `stream_processor.py` 职责过多（约 450 行），需要进行重度拆分重构，符合单一职责原则。

## 架构设计

### 模块职责划分

采用重度拆分，每个模块一个职责：

| 模块 | 位置 | 职责 | 预估行数 |
|------|------|------|---------|
| **StreamProcessor** | `backend/services/stream_processor.py` | WebSocket 连接主入口，消息分发，协调各个服务 | ~150 |
| **AsrStreamProcessor** | `backend/services/asr_stream_processor.py` | 音频块接收，流式 ASR 连接管理，静音超时检测，结果回调 | ~250 |
| **ConversationHistory** | `backend/services/conversation_history.py` | 对话历史增删查改，上下文裁剪（保留最近 N 条） | ~80 |
| **LlmPipeline** | `backend/services/llm_pipeline.py` | LLM 调用，工具调用循环，结果流式输出 | ~200 |
| **tool_definitions** | `backend/services/tool_calling/tool_definitions.py` | 所有工具的元数据定义（名称、描述、参数 schema） | ~60 |
| **ToolExecutor** | `backend/services/tool_calling/tool_executor.py` | 根据 LLM 工具调用分发到具体工具，执行，返回结果 | ~80 |
| **OpenWebSearchClient** | `backend/services/tool_calling/open_websearch_client.py` | HTTP 客户端，调用 open-websearch 守护进程的所有工具 | ~120 |

### 数据流

```
1. WebSocket 收到消息
   ↓
2. StreamProcessor 根据消息类型分发
   - audio_chunk → AsrStreamProcessor.process_audio_chunk()
   - camera_frame → 存储最新帧（保留在 StreamProcessor）
   - user_transcript → 直接添加到对话，触发 LlmPipeline.run()
   - toggle_* → 直接处理状态切换
   ↓
3. AsrStreamProcessor 检测静音超时
   ↓
4. AsrStreamProcessor 回调 StreamProcessor
   ↓
5. StreamProcessor 将最终文本添加到 ConversationHistory
   ↓
6. StreamProcessor 调用 LlmPipeline.run()
   ↓
7. LlmPipeline 构建 LLM 消息，调用 LLM (Anthropic/OpenAI)
   ↓
8. LLM 返回 → 如果有工具调用
   ↓
9. LlmPipeline 将工具调用交给 ToolExecutor.execute()
   ↓
10. ToolExecutor 根据工具名调用 OpenWebSearchClient 对应方法
   ↓
11. OpenWebSearchClient HTTP 调用 open-websearch 守护进程
   ↓
12. 工具结果返回 → LlmPipeline 添加到对话 → 重新调用 LLM
   ↓
13. 重复直到 LLM 不再调用工具 → 输出最终回答
   ↓
14. 最终回答添加到 ConversationHistory
   ↓
15. TTS 合成 → 输出到 WebSocket
```

### 配置

代码中默认配置：

```python
# 在 backend/config.py 的 Settings 类中新增
open_websearch_enabled: bool = True
open_websearch_base_url: str = "http://localhost:3000"
open_websearch_timeout: int = 30
```

用户可通过环境变量覆盖：
```env
# 在 .env 中添加（可选，默认值已在代码中）
OPEN_WEBSEARCH_ENABLED=true
OPEN_WEBSEARCH_BASE_URL=http://localhost:3000
OPEN_WEBSEARCH_TIMEOUT=30
```

### 系统提示词

```
你是一个友好的AI助手，可以看到用户的摄像头画面并进行对话。请保持回答简洁自然。

你可以使用以下网络工具获取信息：

- search: 搜索网页获取实时信息。使用场景：
  * 当前实时信息
  * 最近发生的新闻和事件
  * 你不确定的事实性问题
  * 需要从互联网获取的最新数据
  参数：query (string) - 搜索关键词

- fetchWebContent: 获取完整网页内容。使用场景：
  * 搜索结果摘要不够，需要阅读完整文章内容时
  * 用户要求获取某个 URL 的具体内容
  参数：url (string) - 要获取的网页 URL

- fetchGithubReadme: 获取 GitHub 仓库的 README 文档。使用场景：
  * 用户询问某个 GitHub 项目的信息时
  参数：url (string) - GitHub 仓库 URL

调用工具后，我会将工具返回的结果提供给你，你可以基于结果给出最终回答。
```

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 守护进程未运行 | 返回错误信息"Open-websearch 守护进程未运行，请确保 `open-websearch serve` 已启动"，LLM 自然告诉用户 |
| 搜索超时 | 返回"搜索超时，请稍后重试" |
| 工具执行异常 | 捕获异常，将错误信息作为工具结果返回给 LLM |
| 超过最大迭代次数 | 停止循环（最大 5 次），让 LLM 用已有信息回答 |
| 网络错误 | 捕获异常，返回错误信息给 LLM |

## 日志设计

- **`log_full.log`**: 记录尽可能多的调用细节，包括：
  - ASR 连接状态、每个音频块处理
  - LLM 消息构建细节
  - 工具调用的参数
  - HTTP 请求/响应状态
  - 工具执行结果

- **`log_main.log`**: 只记录核心信息：
  - 静音超时触发 LLM 处理
  - LLM 调用开始/结束
  - 工具调用开始/结束
  - 错误信息

使用项目现有的 logger 配置，按上述级别输出。

## 测试策略

### 第一步：重构完成后编写单元测试

| 测试文件 | 测试内容 |
|----------|---------|
| `tests/test_asr_stream_processor.py` | 测试 ASR 流处理和静音超时检测 |
| `tests/test_conversation_history.py` | 测试对话历史管理和上下文裁剪 |
| `tests/test_open_websearch_client.py` | 测试 open-websearch HTTP 客户端各方法 |
| `tests/test_tool_executor.py` | 测试工具执行分发 |

### 第二步：集成测试

| 测试文件 | 测试内容 |
|----------|---------|
| `tests/test_llm_pipeline_with_tools.py` | 测试完整 LLM + 工具调用流程 |

### 第三步：端到端测试（chrome-devtools MCP）

1. 启动 open-websearch 守护进程: `open-websearch serve`
2. 启动 FastAPI 后端: `cd backend && uvicorn main:app --reload --port 8000`
3. 启动前端开发服务器: `cd frontend && npm run dev`
4. 使用 chrome-devtools MCP 打开 `http://localhost:5173`
5. 登录进入视频通话页面
6. 在文本框输入测试问题：
   - "今天天气怎么样"
   - "现在几点钟"
   - "今天是几号星期几"
   - "最新的 Claude 版本是多少"
7. 验证工具调用流程正常，LLM 能基于搜索结果正确回答

## 实现顺序

1. 重构第一步：从原 `stream_processor` 抽出 `AsrStreamProcessor`
2. 重构第二步：抽出 `ConversationHistory`
3. 重构第三步：抽出 `LlmPipeline`
4. 重构完成 → 运行单元测试验证
5. 新增功能：创建 `tool_calling` 子包，添加 `OpenWebSearchClient`
6. 添加工具定义和 `ToolExecutor`
7. 修改 Anthropic LLM 和 OpenAI LLM 添加工具调用支持
8. 修改 `LlmPipeline` 添加工具调用循环
9. 运行集成测试
10. 使用 chrome-devtools MCP 进行端到端测试

## 依赖

- 不需要新增 Python 依赖（后端已使用 `httpx`）
- open-websearch 需要安装并以守护进程方式运行：
  - **本地源码构建**：克隆仓库 `https://github.com/Aas-ee/open-webSearch`，`npm install && npm run build`，然后 `npm run serve`

守护进程默认监听 `http://localhost:3000`，Python 后端通过 HTTP 调用它的 API。
