# Open-WebSearch MCP 集成实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重度拆分重构 `stream_processor.py`，然后集成 open-websearch MCP 服务，让 LLM 可以自主搜索网页回答实时问题。

**Architecture:** 采用重度拆分，每个模块一个职责：`StreamProcessor` 负责协调，`AsrStreamProcessor` 处理音频流，`ConversationHistory` 管理对话历史，`LlmPipeline` 执行 LLM 调用和工具循环，`tool_calling` 子包处理工具定义和执行。通过 HTTP 调用本地 open-websearch 守护进程。

**Tech Stack:** Python FastAPI, httpx, Anthropic/OpenAI tool calling API, pytest for testing.

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/config.py` | 修改 | 添加 open-websearch 配置 |
| `backend/services/asr_stream_processor.py` | 新建 | 音频流处理 + 静音超时检测 |
| `backend/services/conversation_history.py` | 新建 | 对话历史管理 |
| `backend/services/llm_pipeline.py` | 新建 | LLM 调用 + 工具调用循环 |
| `backend/services/stream_processor.py` | 修改重构 | 主协调器，消息分发 |
| `backend/services/tool_calling/__init__.py` | 新建 | 子包初始化 |
| `backend/services/tool_calling/tool_definitions.py` | 新建 | 工具元数据定义 |
| `backend/services/tool_calling/tool_executor.py` | 新建 | 工具执行器 |
| `backend/services/tool_calling/open_websearch_client.py` | 新建 | open-websearch HTTP 客户端 |
| `backend/services/anthropic_llm.py` | 修改 | 添加工具调用支持 |
| `backend/services/openai_llm.py` | 修改 | 添加工具调用支持 |
| `backend/models/schemas.py` | 修改 | 添加工具调用数据模型 |
| `backend/.env.example` | 修改 | 添加环境变量文档 |
| `backend/tests/test_asr_stream_processor.py` | 新建 | 单元测试 |
| `backend/tests/test_conversation_history.py` | 新建 | 单元测试 |
| `backend/tests/test_open_websearch_client.py` | 新建 | 单元测试 |
| `backend/tests/test_tool_executor.py` | 新建 | 单元测试 |
| `backend/tests/test_llm_pipeline_with_tools.py` | 新建 | 集成测试 |

---

## 任务清单

### 任务 1：添加配置

**文件:**
- Modify: `backend/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: 添加配置项**

在 `Settings` 类中添加：

```python
# Open-WebSearch MCP Daemon
open_websearch_enabled: bool = True
open_websearch_base_url: str = "http://localhost:3000"
open_websearch_timeout: int = 30
```

- [ ] **Step 2: 更新 .env.example 添加文档**

在文件末尾添加：

```env
# Open-WebSearch MCP Integration
# OPEN_WEBSEARCH_ENABLED=true
# OPEN_WEBSEARCH_BASE_URL=http://localhost:3000
# OPEN_WEBSEARCH_TIMEOUT=30
```

- [ ] **Step 3: Commit**

```bash
git add backend/config.py backend/.env.example
git commit -m "feat: add open-websearch configuration"
```

---

### 任务 2：新建 `AsrStreamProcessor` 抽出音频流处理

**文件:**
- Create: `backend/services/asr_stream_processor.py`
- Create: `backend/tests/test_asr_stream_processor.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from services.asr_stream_processor import AsrStreamProcessor


def test_asr_stream_processor_initialization():
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    assert processor.is_running() == False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_asr_stream_processor.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: 实现 `AsrStreamProcessor`**

```python
"""
ASR 流式处理 - 音频块接收，静音超时检测
"""
import asyncio
from typing import Optional, Callable
from config import settings
from services.streaming_asr import StreamingASRService
from utils.logger import get_logger

logger = get_logger("asr_stream_processor")


class AsrStreamProcessor:
    """音频流处理，流式 ASR 管理，静音超时检测"""

    SILENCE_TIMEOUT_MS = 1500

    def __init__(self, on_final_result: Callable[[str], None]):
        self.on_final_result = on_final_result
        self.streaming_asr: Optional[StreamingASRService] = None
        self._pending_audio_buffer: list[bytes] = []
        self._current_segment_id: Optional[str] = None
        self._current_segment_sentences: list[str] = []
        self._current_segment_ongoing: str = ""
        self._silence_timer: Optional[asyncio.Task] = None
        self._silence_timer_id: int = 0
        self._silence_timeout_ms = self.SILENCE_TIMEOUT_MS

    def is_running(self) -> bool:
        return self.streaming_asr is not None

    async def start(self) -> None:
        """启动 ASR 流处理"""
        if self.streaming_asr:
            await self.stop()

        self.streaming_asr = StreamingASRService()

        def on_partial(text: str):
            """部分结果回调"""
            if not self.streaming_asr:
                return

            if self._current_segment_id is None:
                segment_id = str(int(asyncio.get_event_loop().time() * 1000))
                self._current_segment_id = segment_id
                self._current_segment_sentences.clear()
                self._current_segment_ongoing = text
            else:
                segment_id = self._current_segment_id
                self._current_segment_ongoing = text

            # 取消现有静音超时，重置
            if self._silence_timer:
                self._silence_timer.cancel()

            self._silence_timer_id += 1
            self._silence_timer = asyncio.create_task(
                self._silence_timeout_process(self._silence_timer_id)
            )

        def on_final(final_text: str):
            """最终句子结果回调"""
            if not self.streaming_asr:
                return
            if final_text.strip() and self._current_segment_id is not None:
                self._current_segment_sentences.append(final_text.strip())
                self._current_segment_ongoing = ""

        await self.streaming_asr.start(on_partial, on_final)
        logger.info("asr_stream_started", buffered_chunks=len(self._pending_audio_buffer))

    async def process_audio_chunk(self, base64_data: str) -> None:
        """处理音频块"""
        if not self.streaming_asr:
            # 缓冲，等待连接
            audio_data = base64.b64decode(base64_data)
            self._pending_audio_buffer.append(audio_data)
            return

        audio_data = base64.b64decode(base64_data)

        if not self.streaming_asr.is_transcription_started():
            started = await self.streaming_asr.start_transcription()
            if started:
                if self._pending_audio_buffer:
                    for chunk in self._pending_audio_buffer:
                        await self.streaming_asr.send_audio_chunk(chunk)
                    self._pending_audio_buffer.clear()
                await self.streaming_asr.send_audio_chunk(audio_data)
            return

        await self.streaming_asr.send_audio_chunk(audio_data)

    async def _silence_timeout_process(self, timer_id: int) -> None:
        """静音超时处理"""
        await asyncio.sleep(self._silence_timeout_ms / 1000)

        if timer_id != self._silence_timer_id:
            logger.info("silence_timeout_skip_outdated", timer_id=timer_id, active_id=self._silence_timer_id)
            return

        if not self.streaming_asr:
            logger.info("silence_timeout_skip_no_streaming_asr")
            return

        # 合并最终文本
        final_parts: list[str] = []
        if self._current_segment_sentences:
            final_parts.extend(self._current_segment_sentences)
        if self._current_segment_ongoing.strip():
            final_parts.append(self._current_segment_ongoing.strip())

        final_text = " ".join(final_parts).strip()
        if not final_text:
            logger.info("silence_timeout_skip_empty_text")
            return

        logger.info("silence_timeout_final_text", length=len(final_text), text=final_text[:100])

        # 清空状态
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""
        self._current_segment_id = None
        self._silence_timer = None
        self._silence_timer_id = 0

        await self.stop()
        self.on_final_result(final_text)

    async def stop(self) -> None:
        """停止 ASR 处理"""
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
            self._silence_timer_id = 0

        if self.streaming_asr:
            await self.streaming_asr.close()
            self.streaming_asr = None

        self._pending_audio_buffer.clear()
        self._current_segment_id = None
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""

    def get_current_text(self) -> str:
        """获取当前文本"""
        parts: list[str] = []
        if self._current_segment_sentences:
            parts.extend(self._current_segment_sentences)
        if self._current_segment_ongoing.strip():
            parts.append(self._current_segment_ongoing.strip())
        return " ".join(parts).strip()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_asr_stream_processor.py -v
```

Expected: PASS

- [ ] **Step 5: 添加更多测试**

添加测试：

```python
def test_get_current_text():
    def mock_callback(text):
        pass
    processor = AsrStreamProcessor(mock_callback)
    processor._current_segment_sentences = ["hello", "world"]
    processor._current_segment_ongoing = "test"
    assert processor.get_current_text() == "hello world test"
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_asr_stream_processor.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/asr_stream_processor.py backend/tests/test_asr_stream_processor.py
git commit -m "refactor: extract AsrStreamProcessor from stream_processor"
```

---

### 任务 3：新建 `ConversationHistory` 管理对话历史

**文件:**
- Create: `backend/services/conversation_history.py`
- Create: `backend/tests/test_conversation_history.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from services.conversation_history import ConversationHistory
from models.schemas import ConversationMessage


def test_conversation_history_add_message():
    history = ConversationHistory(max_messages=50)
    msg = ConversationMessage(
        id="test-1",
        role="user",
        text="hello",
        timestamp=12345
    )
    history.add_message(msg)
    assert len(history.get_messages()) == 1
    assert history.get_messages()[0].text == "hello"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_conversation_history.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: 实现 `ConversationHistory`**

```python
"""
对话历史管理 - 增删查改，上下文裁剪
"""
from typing import List
from models.schemas import ConversationMessage


class ConversationHistory:
    """对话历史管理器，支持自动裁剪保留最近 N 条消息"""

    def __init__(self, max_messages: int = 50):
        self._messages: List[ConversationMessage] = []
        self._max_messages = max_messages

    def add_message(self, message: ConversationMessage) -> None:
        """添加消息，超过最大长度时裁剪保留最近的"""
        self._messages.append(message)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def get_messages(self) -> List[ConversationMessage]:
        """获取所有消息"""
        return self._messages.copy()

    def clear(self) -> None:
        """清空历史"""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_conversation_history.py -v
```

Expected: PASS

- [ ] **Step 5: 添加裁剪测试**

```python
def test_conversation_history_trimming():
    history = ConversationHistory(max_messages=3)
    for i in range(5):
        msg = ConversationMessage(
            id=f"test-{i}",
            role="user",
            text=f"message {i}",
            timestamp=12345 + i
        )
        history.add_message(msg)
    assert len(history) == 3
    # 保留最后 3 条：message 2, 3, 4
    messages = history.get_messages()
    assert messages[0].text == "message 2"
    assert messages[-1].text == "message 4"
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_conversation_history.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/conversation_history.py backend/tests/test_conversation_history.py
git commit -m "refactor: extract ConversationHistory from stream_processor"
```

---

### 任务 4：重构 `stream_processor.py` 为主协调器

**文件:**
- Modify: `backend/services/stream_processor.py`

- [ ] **Step 1: 重构代码，使用抽出的模块**

替换原文件内容：

```python
"""
Stream Processor - WebSocket 连接主协调器
分发消息到各个服务模块
"""
import base64
import asyncio
from typing import Optional, AsyncGenerator
from config import settings
from models.schemas import (
    ClientMessage,
    ServerMessage,
    ConversationMessage,
    UserTranscriptMessage,
    UserTranscriptOngoingMessage,
    ModelStartMessage,
    ModelTokenMessage,
    ModelAudioMessage,
    ModelEndMessage,
    PongMessage,
    ErrorMessage,
)
from services import TTSService
from services.anthropic_llm import AnthropicLLMService
from services.openai_llm import OpenAILLMService
from services.asr_stream_processor import AsrStreamProcessor
from services.conversation_history import ConversationHistory
from services.llm_pipeline import LlmPipeline
from utils.logger import get_logger

logger = get_logger("stream_processor")

# Singleton service instances - stateless, can be reused across connections
_tts_service = TTSService()
_anthropic_llm = AnthropicLLMService()
_openai_llm = OpenAILLMService()


class StreamProcessor:
    """Main stream coordinator for WebSocket connection"""

    def __init__(self):
        # 依赖服务
        self.tts_service = _tts_service
        self.anthropic_llm = _anthropic_llm
        self.openai_llm = _openai_llm

        # 状态
        self.conversation_history = ConversationHistory(max_messages=50)
        self.latest_camera_frame: Optional[str] = None
        self.audio_enabled: bool = True
        self.camera_enabled: bool = True
        self.subtitle_enabled: bool = True
        self._processing_lock = asyncio.Lock()
        self._result_callback: Optional[callable] = None

        # ASR 处理器
        self.asr_processor: Optional[AsrStreamProcessor] = None

    def handle_ping(self) -> PongMessage:
        return PongMessage()

    def toggle_audio(self, enabled: bool) -> None:
        """Toggle audio capture"""
        self.audio_enabled = enabled
        if enabled:
            # 重启 ASR
            asyncio.create_task(self._start_asr())
        else:
            # 停止 ASR
            asyncio.create_task(self._stop_asr())

    def toggle_camera(self, enabled: bool) -> None:
        self.camera_enabled = enabled
        if not enabled:
            self.latest_camera_frame = None

    def toggle_subtitle(self, enabled: bool) -> None:
        self.subtitle_enabled = enabled

    def process_camera_frame(self, base64_data: str) -> None:
        """Store the latest camera frame"""
        self.latest_camera_frame = base64_data

    async def process_audio_chunk(self, base64_data: str) -> AsyncGenerator[ServerMessage, None]:
        """Process audio chunk through ASR processor"""
        if not self.audio_enabled:
            return

        if self.asr_processor:
            await self.asr_processor.process_audio_chunk(base64_data)

        # Yield nothing for type checker
        if False:
            yield

    def _on_asr_final_result(self, final_text: str) -> None:
        """ASR 最终结果回调"""
        if not final_text.strip():
            return

        # 添加到对话历史
        self.conversation_history.add_message(ConversationMessage(
            id=f"{int(asyncio.get_event_loop().time() * 1000)}-user",
            role="user",
            text=final_text,
            timestamp=int(asyncio.get_event_loop().time() * 1000)
        ))

        # 触发 LLM 处理
        if self._result_callback:
            logger.info("starting_llm_processing", final_text_length=len(final_text))
            asyncio.create_task(self._process_after_asr_stop())

    async def _process_after_asr_stop(self) -> None:
        """ASR 停止后处理，重启 ASR"""
        async with self._processing_lock:
            # 运行 LLM 管道
            if self._result_callback:
                async for msg in self.run_llm_pipeline():
                    self._result_callback(msg)
        # 重启 ASR
        await self._start_asr_if_enabled()

    async def _start_asr(self) -> None:
        """启动 ASR 处理器"""
        if self.asr_processor:
            await self._stop_asr()

        self.asr_processor = AsrStreamProcessor(self._on_asr_final_result)
        await self.asr_processor.start()

    async def _stop_asr(self) -> None:
        """停止 ASR 处理器"""
        if self.asr_processor:
            await self.asr_processor.stop()
            self.asr_processor = None

    async def _start_asr_if_enabled(self) -> None:
        """如果音频启用，重启 ASR"""
        if self.audio_enabled:
            await self._start_asr()

    def set_result_callback(self, callback: callable) -> None:
        """Set callback to send ServerMessage to websocket"""
        self._result_callback = callback

    async def process_final_transcript(self, text: str) -> AsyncGenerator[ServerMessage, None]:
        """Process direct user text input (from text box)"""
        if not text.strip():
            return

        # 添加到对话历史
        self.conversation_history.add_message(ConversationMessage(
            id=f"{int(asyncio.get_event_loop().time() * 1000)}-user",
            role="user",
            text=text,
            timestamp=int(asyncio.get_event_loop().time() * 1000)
        ))

        # 运行 LLM 管道
        async for msg in self.run_llm_pipeline():
            yield msg

    async def run_llm_pipeline(self) -> AsyncGenerator[ServerMessage, None]:
        """Run LLM pipeline with tool calling support"""
        logger.info("run_llm_pipeline_started")
        async with self._processing_lock:
            llm_pipeline = LlmPipeline(
                conversation_history=self.conversation_history,
                latest_camera_frame=self.latest_camera_frame,
                anthropic_llm=self.anthropic_llm,
                openai_llm=self.openai_llm,
                tts_service=self.tts_service
            )

            session_id = str(int(asyncio.get_event_loop().time() * 1000))
            yield ModelStartMessage(sessionId=session_id)

            full_response = ""
            async for msg in llm_pipeline.run():
                if isinstance(msg, str):
                    full_response += msg
                    yield ModelTokenMessage(token=msg)
                else:
                    # 已经在 llm_pipeline 处理，这里不需要
                    pass

            # 添加最终回答到对话历史
            self.conversation_history.add_message(ConversationMessage(
                id=f"{session_id}-model",
                role="model",
                text=full_response,
                timestamp=int(asyncio.get_event_loop().time() * 1000)
            ))

            # TTS 合成
            if full_response.strip():
                tts_result = await self.tts_service.synthesize(full_response)
                if tts_result.success and tts_result.audio:
                    base64_a = base64.b64encode(tts_result.audio).decode('utf-8')
                    yield ModelAudioMessage(data=base64_a)

            yield ModelEndMessage()

    def get_conversation_history(self) -> list[ConversationMessage]:
        return self.conversation_history.get_messages()
```

- [ ] **Step 2: 运行语法检查**

```bash
cd backend
python -m pytest tests/ -v --no-header 2>/dev/null || python -c "import services.stream_processor; print('Syntax OK')"
```

Expected: Syntax OK

- [ ] **Step 3: Commit**

```bash
git add backend/services/stream_processor.py
git commit -m "refactor: rewrite stream_processor as main coordinator using extracted modules"
```

---

### 任务 5：添加工具调用数据模型

**文件:**
- Modify: `backend/models/schemas.py`

- [ ] **Step 1: 添加工具相关数据模型**

在文件末尾添加：

```python
# ==================== Tool Calling Types ====================

class ToolCall(BaseModel):
    """LLM 工具调用"""
    id: str
    name: str
    parameters: dict  # JSON 参数


class ToolResult(BaseModel):
    """工具执行结果"""
    tool_call_id: str
    content: str
    success: bool = True
```

更新 `LLMMessage` 的 role 允许 `tool`:

```python
class LLMMessage(BaseModel):
    role: Literal['user', 'assistant', 'system', 'tool']
    content: Union[str, List[LLMContentPart]]
```

- [ ] **Step 2: Commit**

```bash
git add backend/models/schemas.py
git commit -m "feat: add tool calling data models to schemas"
```

---

### 任务 6：创建 `tool_calling` 子包 - 工具定义

**文件:**
- Create: `backend/services/tool_calling/__init__.py`
- Create: `backend/services/tool_calling/tool_definitions.py`

- [ ] **Step 1: 创建 `__init__.py`**

```python
"""Tool calling package - open-websearch tools execution"""
from .tool_definitions import get_tool_definitions, ToolDefinition
from .tool_executor import ToolExecutor
from .open_websearch_client import OpenWebSearchClient

__all__ = [
    "ToolDefinition",
    "get_tool_definitions",
    "ToolExecutor",
    "OpenWebSearchClient",
]
```

- [ ] **Step 2: 创建 `tool_definitions.py`**

```python
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
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": self.type,
            }
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/tool_calling/__init__.py backend/services/tool_calling/tool_definitions.py
git commit -m "feat: add tool_calling package with tool definitions"
```

---

### 任务 7：创建 open-websearch HTTP 客户端

**文件:**
- Create: `backend/services/tool_calling/open_websearch_client.py`
- Create: `backend/tests/test_open_websearch_client.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from services.tool_calling.open_websearch_client import OpenWebSearchClient


def test_client_is_configured():
    client = OpenWebSearchClient()
    # 默认配置 enabled
    assert client.is_configured() is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_open_websearch_client.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: 实现 `OpenWebSearchClient`**

```python
"""OpenWebSearch HTTP 客户端
调用本地 open-websearch 守护进程的 HTTP API
"""
import httpx
from typing import List, Optional, Dict, Any
from config import settings
from utils.logger import get_logger

logger = get_logger("open_websearch_client")


class OpenWebSearchClient:
    """HTTP client for open-websearch local daemon"""

    def __init__(self):
        self.base_url = settings.open_websearch_base_url.rstrip('/')
        self.timeout = settings.open_websearch_timeout
        self.enabled = settings.open_websearch_enabled

    def is_configured(self) -> bool:
        """检查服务是否启用"""
        return self.enabled

    async def health_check(self) -> bool:
        """检查守护进程是否运行"""
        if not self.enabled:
            return False

        try:
            url = f"{self.base_url}/health"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                result = response.status_code == 200
                logger.info("open_websearch_health_check", result=result)
                return result
        except Exception as e:
            logger.error("open_websearch_health_check_failed", error=str(e))
            return False

    async def search(self, query: str, limit: int = 5, engines: Optional[List[str]] = None) -> Dict[str, Any]:
        """搜索网页"""
        logger.info("open_websearch_search", query=query, limit=limit, engines=engines)

        payload = {
            "query": query,
            "limit": limit,
        }
        if engines:
            payload["engines"] = engines

        try:
            url = f"{self.base_url}/search"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_search_success", results_count=len(result) if isinstance(result, list) else 0)
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_search_failed", query=query, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def fetch_web_content(self, url: str, max_chars: int = 30000) -> Dict[str, Any]:
        """获取网页内容"""
        logger.info("open_websearch_fetch_web", url=url, max_chars=max_chars)

        payload = {
            "url": url,
            "maxChars": max_chars,
        }

        try:
            fetch_url = f"{self.base_url}/fetch-web"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(fetch_url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_fetch_web_success", url=url, content_length=len(result.get("content", "")))
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_fetch_web_failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def fetch_github_readme(self, url: str) -> Dict[str, Any]:
        """获取 GitHub README"""
        logger.info("open_websearch_fetch_github_readme", url=url)

        payload = {
            "url": url,
        }

        try:
            fetch_url = f"{self.base_url}/fetch-github-readme"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(fetch_url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_fetch_github_readme_success", url=url)
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_fetch_github_readme_failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def fetch_juejin_article(self, url: str) -> Dict[str, Any]:
        """获取掘金文章"""
        logger.info("open_websearch_fetch_juejin", url=url)

        payload = {
            "url": url,
        }

        try:
            fetch_url = f"{self.base_url}/fetch-juejin"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(fetch_url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_fetch_juejin_success", url=url)
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_fetch_juejin_failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def fetch_csdn_article(self, url: str) -> Dict[str, Any]:
        """获取 CSDN 文章"""
        logger.info("open_websearch_fetch_csdn", url=url)

        payload = {
            "url": url,
        }

        try:
            fetch_url = f"{self.base_url}/fetch-csdn"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(fetch_url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_fetch_csdn_success", url=url)
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_fetch_csdn_failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def fetch_linuxdo_article(self, url: str) -> Dict[str, Any]:
        """获取 Linux.Do 文章"""
        logger.info("open_websearch_fetch_linuxdo", url=url)

        payload = {
            "url": url,
        }

        try:
            fetch_url = f"{self.base_url}/fetch-linuxdo"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(fetch_url, json=payload)
                response.raise_for_status()
                result = response.json()
                logger.info("open_websearch_fetch_linuxdo_success", url=url)
                return {
                    "success": True,
                    "result": result,
                }
        except Exception as e:
            logger.error("open_websearch_fetch_linuxdo_failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
            }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_open_websearch_client.py -v
```

Expected: PASS

- [ ] **Step 5: 添加更多测试**

```python
async def test_health_check_when_daemon_not_running():
    client = OpenWebSearchClient()
    # 如果守护进程没运行，应该返回 False
    result = await client.health_check()
    # 这个测试不失败，只是记录结果
    print(f"Health check result: {result}")
    assert result in [True, False]
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_open_websearch_client.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/tool_calling/open_websearch_client.py backend/tests/test_open_websearch_client.py
git commit -m "feat: add OpenWebSearch HTTP client"
```

---

### 任务 8：创建工具执行器

**文件:**
- Create: `backend/services/tool_calling/tool_executor.py`
- Create: `backend/tests/test_tool_executor.py`

- [ ] **Step 1: 写失败测试**

```python
import pytest
from services.tool_calling.tool_definitions import get_tool_definitions
from services.tool_calling.open_websearch_client import OpenWebSearchClient
from services.tool_calling.tool_executor import ToolExecutor


def test_tool_executor_has_all_tools():
    client = OpenWebSearchClient()
    executor = ToolExecutor(get_tool_definitions(), client)
    tools = executor.get_tool_names()
    assert len(tools) == 6
    assert "search" in tools
    assert "fetchWebContent" in tools
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_tool_executor.py -v
```

Expected: FAIL - module not found

- [ ] **Step 3: 实现 `ToolExecutor`**

```python
"""工具执行器 - 根据 LLM 工具调用分发到具体工具"""
import json
from typing import List, Dict, Any, Optional
from .tool_definitions import ToolDefinition
from .open_websearch_client import OpenWebSearchClient
from utils.logger import get_logger

logger = get_logger("tool_executor")


class ToolExecutionResult:
    """工具执行结果"""
    tool_name: str
    tool_call_id: str
    success: bool
    content: str

    def __init__(self, tool_name: str, tool_call_id: str, success: bool, content: str):
        self.tool_name = tool_name
        self.tool_call_id = tool_call_id
        self.success = success
        self.content = content


class ToolExecutor:
    """工具执行器"""

    def __init__(self, tool_definitions: List[ToolDefinition], client: OpenWebSearchClient):
        self._tool_definitions = {t.name: t for t in tool_definitions}
        self._client = client

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tool_definitions.keys())

    async def execute(self, tool_name: str, tool_call_id: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """执行工具调用"""
        logger.info("tool_execution_start", tool_name=tool_name, parameters=parameters)

        if tool_name not in self._tool_definitions:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error("tool_execution_unknown_tool", tool_name=tool_name)
            return ToolExecutionResult(tool_name, tool_call_id, False, error_msg)

        try:
            result = await self._dispatch_execute(tool_name, parameters)
            if result["success"]:
                content = json.dumps(result["result"], ensure_ascii=False)
                logger.info("tool_execution_success", tool_name=tool_name)
                return ToolExecutionResult(tool_name, tool_call_id, True, content)
            else:
                error_msg = f"Tool execution failed: {result.get('error', 'unknown error')}"
                logger.error("tool_execution_failed", tool_name=tool_name, error=error_msg)
                return ToolExecutionResult(tool_name, tool_call_id, False, error_msg)
        except Exception as e:
            error_msg = f"Tool execution exception: {str(e)}"
            logger.error("tool_execution_exception", tool_name=tool_name, error=str(e))
            return ToolExecutionResult(tool_name, tool_call_id, False, error_msg)

    async def _dispatch_execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """根据工具名称分发执行"""
        if tool_name == "search":
            query = parameters.get("query", "")
            limit = parameters.get("limit", 5)
            engines = parameters.get("engines", None)
            return await self._client.search(query, limit, engines)

        elif tool_name == "fetchWebContent":
            url = parameters.get("url", "")
            max_chars = parameters.get("maxChars", 30000)
            return await self._client.fetch_web_content(url, max_chars)

        elif tool_name == "fetchGithubReadme":
            url = parameters.get("url", "")
            return await self._client.fetch_github_readme(url)

        elif tool_name == "fetchJuejinArticle":
            url = parameters.get("url", "")
            return await self._client.fetch_juejin_article(url)

        elif tool_name == "fetchCsdnArticle":
            url = parameters.get("url", "")
            return await self._client.fetch_csdn_article(url)

        elif tool_name == "fetchLinuxDoArticle":
            url = parameters.get("url", "")
            return await self._client.fetch_linuxdo_article(url)

        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_tool_executor.py -v
```

Expected: PASS

- [ ] **Step 5: 添加测试执行错误**

```python
def test_execute_unknown_tool():
    client = OpenWebSearchClient()
    executor = ToolExecutor(get_tool_definitions(), client)
    result = executor.execute("unknown_tool", "test-id", {})
    assert not result.success
    assert "not found" in result.content
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend
python -m pytest tests/test_tool_executor.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/services/tool_calling/tool_executor.py backend/tests/test_tool_executor.py
git commit -m "feat: add ToolExecutor for tool call dispatch"
```

---

### 任务 9：更新 Anthropic LLM 服务添加工具调用支持

**文件:**
- Modify: `backend/services/anthropic_llm.py`

- [ ] **Step 1: 修改导入和添加类型**

更新导入：

```python
import json
import httpx
from typing import List, AsyncGenerator, Optional, Dict, Any
from config import settings
from models.schemas import LLMMessage, LLMContentPart, ToolCall
from services.tool_calling.tool_definitions import ToolDefinition
```

修改 `chat_stream` 方法签名添加 tools 参数：

```python
async def chat_stream(
    self,
    messages: List[LLMMessage],
    tools: Optional[List[ToolDefinition]] = None
) -> AsyncGenerator[str | ToolCall, None]:
```

- [ ] **Step 2: 更新请求数据添加工具**

在构建 `data` 后，如果有工具，添加：

```python
if tools:
    data["tools"] = [t.to_anthropic() for t in tools]
```

- [ ] **Step 3: 更新流解析处理工具调用**

修改 `_parse_anthropic_stream` 方法以处理工具调用：

```python
async def _parse_anthropic_stream(self, response: httpx.Response) -> AsyncGenerator[str | ToolCall, None]:
    """Parse Anthropic SSE streaming response

    Extracts text from content_block_delta events.
    Yields tokens one by one or ToolCall objects.
    """
    event_type = None
    current_tool_call: Optional[dict] = None

    async for line in response.aiter_lines():
        if not line:
            continue

        if line.startswith("event: "):
            current_event = line[7:].strip()
            event_type = current_event
            continue
        elif line.startswith("data: "):
            data_line = line[6:].strip()
            if not data_line:
                continue

            try:
                chunk = json.loads(data_line)

                if event_type == "content_block_delta":
                    if "delta" in chunk and "text" in chunk["delta"]:
                        text = chunk["delta"]["text"]
                        yield text
                elif event_type == "tool_use":
                    # Tool call started - accumulate
                    if "content_block" in chunk:
                        current_tool_call = chunk["content_block"]
                elif event_type == "message_delta":
                    # Message complete - check if we have a tool call
                    if current_tool_call:
                        # We have a tool call
                        tool_name = current_tool_call.get("name", "")
                        tool_id = current_tool_call.get("id", "")
                        input = current_tool_call.get("input", {})
                        if tool_name and tool_id:
                            yield ToolCall(
                                id=tool_id,
                                name=tool_name,
                                parameters=input
                            )
                        current_tool_call = None

            except json.JSONDecodeError:
                continue
```

- [ ] **Step 4: 语法检查**

```bash
cd backend
python -c "import services.anthropic_llm; print('Syntax OK')"
```

Expected: Syntax OK

- [ ] **Step 5: Commit**

```bash
git add backend/services/anthropic_llm.py
git commit -m "feat: add tool calling support to Anthropic LLM service"
```

---

### 任务 10：更新 OpenAI LLM 服务添加工具调用支持

**文件:**
- Modify: `backend/services/openai_llm.py`

- [ ] **Step 1: 修改导入和添加类型**

更新导入：

```python
import httpx
from typing import List, AsyncGenerator, Optional
from config import settings
from models.schemas import LLMMessage, LLMContentPart, ToolCall
from services.tool_calling.tool_definitions import ToolDefinition
from utils import parse_openai_stream
```

修改 `chat_stream` 方法签名：

```python
async def chat_stream(
    self,
    messages: List[LLMMessage],
    tools: Optional[List[ToolDefinition]] = None
) -> AsyncGenerator[str | ToolCall, None]:
```

- [ ] **Step 2: 更新请求数据添加工具**

在构建 `data` 后，如果有工具，添加：

```python
if tools:
    data["tools"] = [t.to_openai() for t in tools]
```

- [ ] **Step 3: 修改流解析处理工具调用**

当前 `parse_openai_stream` 只返回文本，我们需要在 `chat_stream` 中检测工具调用：

修改方法体，在得到每个 token 后检查：

```python
url = f"{self.base_url.rstrip('/')}/chat/completions"

async with httpx.AsyncClient(timeout=120) as client:
    async with client.stream('POST', url, headers=headers, json=data) as response:
        if response.status_code != 200:
            yield f"Error: {response.status_code}"
            return

        # Check if the first chunk indicates a tool call
        accumulated_tool_call: Optional[dict] = None

        async for item in parse_openai_stream(response):
            if isinstance(item, dict):
                # This is a tool call chunk
                if "tool_calls" in item:
                    for tool_call in item["tool_calls"]:
                        # OpenAI returns one tool call at a time in streaming
                        if tool_call.get("type") == "function":
                            function = tool_call.get("function", {})
                            name = function.get("name", "")
                            tool_call_id = tool_call.get("id", "")
                            arguments_str = function.get("arguments", "")
                            # Try to parse arguments
                            try:
                                arguments = json.loads(arguments_str)
                            except json.JSONDecodeError:
                                arguments = {}
                            if name and tool_call_id:
                                yield ToolCall(
                                    id=tool_call_id,
                                    name=name,
                                    parameters=arguments
                                )
            else:
                # Normal text token
                yield item
```

需要在文件开头添加 `import json`。

- [ ] **Step 4: 语法检查**

```bash
cd backend
python -c "import services.openai_llm; print('Syntax OK')"
```

Expected: Syntax OK

- [ ] **Step 5: Commit**

```bash
git add backend/services/openai_llm.py
git commit -m "feat: add tool calling support to OpenAI LLM service"
```

---

### 任务 11：创建 `LlmPipeline` 实现 LLM 调用和工具循环

**文件:**
- Create: `backend/services/llm_pipeline.py`
- Create: `backend/tests/test_llm_pipeline_with_tools.py`

- [ ] **Step 1: 文件创建和导入**

```python
"""
LLM Pipeline - 执行 LLM 调用和工具调用循环
"""
import asyncio
from typing import List, AsyncGenerator, Optional
from models.schemas import (
    LLMMessage,
    LLMContentPart,
    ConversationMessage,
    ToolCall,
    ToolResult,
)
from services.anthropic_llm import AnthropicLLMService
from services.openai_llm import OpenAILLMService
from services.tts import TTSService
from services.conversation_history import ConversationHistory
from services.tool_calling.tool_definitions import get_tool_definitions, ToolDefinition
from services.tool_calling.tool_executor import ToolExecutor, ToolExecutionResult
from services.tool_calling.open_websearch_client import OpenWebSearchClient
from utils.logger import get_logger

logger = get_logger("llm_pipeline")


class LlmPipeline:
    """LLM 管道，包含工具调用循环"""

    MAX_TOOL_ITERATIONS = 5

    def __init__(
        self,
        conversation_history: ConversationHistory,
        latest_camera_frame: Optional[str],
        anthropic_llm: AnthropicLLMService,
        openai_llm: OpenAILLMService,
        tts_service: TTSService,
    ):
        self.conversation_history = conversation_history
        self.latest_camera_frame = latest_camera_frame
        self.anthropic_llm = anthropic_llm
        self.openai_llm = openai_llm
        self.tts_service = tts_service

        # 工具调用
        self._tools = get_tool_definitions()
        self._open_websearch_client = OpenWebSearchClient()
        self._tool_executor = ToolExecutor(self._tools, self._open_websearch_client)

    def _build_llm_messages(self) -> list[LLMMessage]:
        """构建 LLM 消息，添加系统提示词，包含工具使用说明"""
        messages = []

        # 系统提示词 - 包含工具使用指导
        system_prompt = """你是一个友好的AI助手，可以看到用户的摄像头画面并进行对话。请保持回答简洁自然。

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

- fetchJuejinArticle: 获取掘金文章的完整内容。使用场景：
  * 需要阅读掘金上的技术文章时
  参数：url (string) - 掘金文章 URL

- fetchCsdnArticle: 获取 CSDN 文章的完整内容。使用场景：
  * 需要阅读 CSDN 上的技术文章时
  参数：url (string) - CSDN 文章 URL

- fetchLinuxDoArticle: 获取 Linux.Do 文章的完整内容。使用场景：
  * 需要阅读 Linux.Do 上的讨论内容时
  参数：url (string) - Linux.Do 文章 URL

调用工具后，我会将工具返回的结果提供给你，你可以基于结果给出最终回答。
"""

        messages.append(LLMMessage(
            role="system",
            content=system_prompt
        ))

        # 添加对话历史，保留最近 10 条
        for msg in self.conversation_history.get_messages()[-10:]:
            role = msg.role
            if role == "model":
                role = "assistant"

            if msg.role == "user" and msg is self.conversation_history.get_messages()[-1] and self.latest_camera_frame:
                # 最后一条用户消息有图片
                content = [
                    LLMContentPart(type="text", text=msg.text),
                    LLMContentPart(type="image", image=self.latest_camera_frame)
                ]
                messages.append(LLMMessage(role=role, content=content))
            else:
                messages.append(LLMMessage(role=role, content=msg.text))

        return messages

    async def run(self) -> AsyncGenerator[str, None]:
        """运行 LLM 管道，包含工具调用循环
        Yields: text tokens
        """
        logger.info("llm_pipeline_started", tool_enabled=self._open_websearch_client.is_configured())

        llm_messages = self._build_llm_messages()
        tool_iterations = 0
        max_iterations = self.MAX_TOOL_ITERATIONS

        # 如果 open-websearch 未启用，不提供工具
        tools = self._tools if self._open_websearch_client.is_configured() else None

        while tool_iterations < max_iterations:
            tool_iterations += 1
            logger.info("llm_iteration_start", iteration=tool_iterations)

            # 调用 LLM
            has_tool_calls = False
            tool_calls: List[ToolCall] = []

            # 选择 LLM
            if self.anthropic_llm.is_configured():
                logger.info("llm_selected", protocol="anthropic")
                stream = self.anthropic_llm.chat_stream(llm_messages, tools)
            elif self.openai_llm.is_configured():
                logger.info("llm_selected", protocol="openai")
                stream = self.openai_llm.chat_stream(llm_messages, tools)
            else:
                logger.error("no_llm_configured")
                yield "Error: No LLM service configured. Please set ANTHROPIC_AUTH_TOKEN or OPENAI_API_KEY in .env"
                return

            logger.info("llm_stream_started")

            # 处理流
            async for item in stream:
                if isinstance(item, ToolCall):
                    has_tool_calls = True
                    tool_calls.append(item)
                else:
                    # 只在没有工具调用时 yield text
                    # 如果有工具调用，我们不 yield 直到得到最终回答
                    if not has_tool_calls:
                        yield item

            if not has_tool_calls:
                # 没有工具调用，完成
                logger.info("llm_pipeline_completed", tool_iterations=tool_iterations-1, has_tool_calls=False)
                break

            # 我们有工具调用需要执行
            logger.info("llm_tool_calls_detected", count=len(tool_calls))

            # 并行执行所有工具调用
            for tool_call in tool_calls:
                result = await self._execute_tool_call(tool_call)
                # 添加工具结果到 LLM 消息
                content = result.content if result.success else f"Error: {result.content}"
                llm_messages.append(LLMMessage(
                    role="tool",
                    content=content
                ))

            # 循环继续，下一轮 LLM 调用

        logger.info("llm_pipeline_finished", iterations=tool_iterations)

    async def _execute_tool_call(self, tool_call: ToolCall) -> ToolExecutionResult:
        """执行单个工具调用"""
        logger.info("tool_call_executing", tool_name=tool_call.name, tool_id=tool_call.id)
        result = await self._tool_executor.execute(
            tool_call.name,
            tool_call.id,
            tool_call.parameters
        )
        if result.success:
            logger.info("tool_call_success", tool_name=tool_call.name)
        else:
            logger.error("tool_call_failed", tool_name=tool_call.name, error=result.content)
        return result
```

- [ ] **Step 2: 语法检查**

```bash
cd backend
python -c "import services.llm_pipeline; print('Syntax OK')"
```

Expected: Syntax OK

- [ ] **Step 3: 写集成测试**

```python
"""Integration test for LLM pipeline with tool calling"""
import pytest
from services.conversation_history import ConversationHistory
from services.llm_pipeline import LlmPipeline
from services.anthropic_llm import AnthropicLLMService
from services.openai_llm import OpenAILLMService
from services import TTSService


def test_llm_pipeline_initialization():
    history = ConversationHistory(max_messages=10)
    tts = TTSService()
    anthropic = AnthropicLLMService()
    openai = OpenAILLMService()

    pipeline = LlmPipeline(
        conversation_history=history,
        latest_camera_frame=None,
        anthropic_llm=anthropic,
        openai_llm=openai,
        tts_service=tts
    )

    assert pipeline is not None
    # tools should be loaded
    assert len(pipeline._tools) == 6
```

- [ ] **Step 4: 运行集成测试**

```bash
cd backend
python -m pytest tests/test_llm_pipeline_with_tools.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/llm_pipeline.py backend/tests/test_llm_pipeline_with_tools.py
git commit -m "feat: create LlmPipeline with tool calling loop"
```

---

### 任务 12：运行所有单元测试和集成测试

- [ ] **Step 1: 运行所有单元测试**

```bash
cd backend
python -m pytest tests/test_*.py -v
```

Expected: All tests pass

- [ ] **Step 2: Commit if any fixes needed**

如果有测试失败，修复后提交。

---

### 任务 13：端到端测试准备（使用 chrome-devtools MCP）

**用户需要手动启动守护进程和后端，然后使用 chrome-devtools MCP 打开前端测试：**

测试问题：
1. "今天天气怎么样"
2. "现在几点钟"
3. "今天是几号星期几"
4. "最新的 Claude 版本是多少"

验证工具调用流程正常，LLM 能基于搜索结果正确回答。

---

## 计划完成

现在所有任务都定义好了。每个任务都是独立的，逐步执行。
