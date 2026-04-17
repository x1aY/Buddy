"""
Stream Processor - WebSocket 连接主协调器
分发消息到各个服务模块
"""
import base64
import asyncio
from uuid import UUID
from typing import Optional, AsyncGenerator, List
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
    LLMMessage,
    ConversationTitleUpdatedMessage,
)
from services.llm import (
    BaseLLMService,
    get_llm_service,
    ConversationHistory,
    LlmPipeline,
)
from services.speech import (
    BaseTTSService,
    get_tts_service,
    AsrStreamProcessor,
)
from storage.conversation_storage import update_conversation_title
from utils.logger import get_logger

logger = get_logger("stream_processor")

# Configuration constants for auto-title generation
MAX_TITLE_LENGTH = 10
MAX_MESSAGES_FOR_SUMMARY = 4

# Singleton service instances - stateless, can be reused across connections
_tts_service: BaseTTSService = get_tts_service()
_llm_service: BaseLLMService = get_llm_service()


class StreamProcessor:
    """Main stream coordinator for WebSocket connection"""

    def __init__(self):
        # 依赖服务
        self.tts_service = _tts_service
        self.llm_service = _llm_service

        # 状态
        self.conversation_history = ConversationHistory(max_messages=50)
        self.latest_camera_frame: Optional[str] = None
        self.audio_enabled: bool = True
        self.camera_enabled: bool = True
        self.subtitle_enabled: bool = True
        self.current_conversation_id: Optional[str] = None
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
        try:
            async with self._processing_lock:
                # 运行 LLM 管道
                if self._result_callback:
                    async for msg in self.run_llm_pipeline():
                        self._result_callback(msg)
            # 重启 ASR
            await self._start_asr_if_enabled()
        except Exception as e:
            logger.error("llm_processing_failed", error=str(e), exc_info=True)
            if self._result_callback:
                self._result_callback(ErrorMessage(message=f"LLM 处理失败: {str(e)}"))

    def _on_asr_partial_result(self, segment_id: str, full_text: str) -> None:
        """ASR 部分结果回调 - 发送实时更新到前端"""
        if self._result_callback and self.subtitle_enabled:
            self._result_callback(UserTranscriptOngoingMessage(
                message_id=segment_id,
                text=full_text
            ))

    async def _start_asr(self) -> None:
        """启动 ASR 处理器"""
        if self.asr_processor:
            await self._stop_asr()

        self.asr_processor = AsrStreamProcessor(
            on_final_result=self._on_asr_final_result,
            on_partial_result=self._on_asr_partial_result
        )
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

    def set_current_conversation_id(self, conversation_id: str) -> None:
        """Set current active conversation ID for auto-title generation"""
        self.current_conversation_id = conversation_id

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
        llm_pipeline = LlmPipeline(
            conversation_history=self.conversation_history,
            latest_camera_frame=self.latest_camera_frame,
            llm_service=self.llm_service,
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
                # already handled in llm_pipeline
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
                base64_audio = base64.b64encode(tts_result.audio).decode('utf-8')
                yield ModelAudioMessage(data=base64_audio)

        yield ModelEndMessage()

        # Auto-generate/update conversation title after model finishes
        # Only if we have a conversation ID and at least one user + one model message
        if (
            self.current_conversation_id
            and len(self.conversation_history.get_messages()) >= 2
        ):
            # Run title generation asynchronously (don't block streaming)
            asyncio.create_task(self._generate_and_update_title())

    def get_conversation_history(self) -> list[ConversationMessage]:
        return self.conversation_history.get_messages()

    async def _generate_and_update_title(self) -> None:
        """Generate a conversation title (max 10 Chinese characters) and update it"""
        try:
            messages = self.conversation_history.get_messages()

            # Build conversation content for summarization
            conversation_text = ""
            for msg in messages[-MAX_MESSAGES_FOR_SUMMARY:]:
                role = "用户" if msg.role == "user" else "AI"
                conversation_text += f"{role}: {msg.text}\n"

            # Build prompt for title generation
            prompt = f"""请用不超过{MAX_TITLE_LENGTH}个汉字总结这个对话的主题。只输出标题，不需要其他解释，不要超过{MAX_TITLE_LENGTH}个字。

对话内容：
{conversation_text}

标题："""

            # Call LLM to generate title - use chat_stream and collect all tokens
            llm_messages: List[LLMMessage] = [
                LLMMessage(
                    role="system",
                    content="你是一个对话总结助手，擅长用简洁的语言总结对话主题。"
                ),
                LLMMessage(
                    role="user",
                    content=prompt
                )
            ]

            # Full completion for title - collect all tokens from stream
            title = ""
            async for token in self.llm_service.chat_stream(llm_messages):
                title += token

            # Clean up title - remove extra whitespace, newlines, quotes
            title = title.strip().strip('"').strip("'").strip()

            # Truncate to max MAX_TITLE_LENGTH characters (Chinese characters count as 1)
            if len(title) > MAX_TITLE_LENGTH:
                title = title[:MAX_TITLE_LENGTH]

            if not title:
                # Fallback: use first few characters of last user message
                last_user_msg = next((m for m in reversed(messages) if m.role == "user"), None)
                if last_user_msg:
                    title = last_user_msg.text[:MAX_TITLE_LENGTH]

            # Update title in storage
            if title:
                update_conversation_title(UUID(self.current_conversation_id), title)
                logger.info("conversation_title_updated", title=title, conversation_id=self.current_conversation_id)
                # Notify frontend that title has been updated
                if self._result_callback:
                    self._result_callback(ConversationTitleUpdatedMessage(title=title))

        except Exception as e:
            # Title generation should not fail the main conversation flow
            logger.error("title_generation_failed", error=str(e), exc_info=True)