import base64
import asyncio
from typing import Optional, AsyncGenerator
from config import settings
from models.schemas import (
    ClientMessage,
    ServerMessage,
    ConversationMessage,
    LLMMessage,
    LLMContentPart,
    UserTranscriptMessage,
    ModelStartMessage,
    ModelTokenMessage,
    ModelAudioMessage,
    ModelEndMessage,
    PongMessage,
    ErrorMessage,
)
from services import ASRService, TTSService, DoubaoLLMService, VolcanoCodingService

# Singleton service instances - stateless, can be reused across connections
_asr_service = ASRService()
_tts_service = TTSService()
_doubao_llm = DoubaoLLMService()
_volcano_coding = VolcanoCodingService()


class StreamProcessor:
    """Process incoming media stream and handle conversation"""

    def __init__(self):
        # Reuse singleton service instances
        self.asr_service = _asr_service
        self.tts_service = _tts_service
        self.doubao_llm = _doubao_llm
        self.volcano_coding = _volcano_coding
        self.conversation_history: list[ConversationMessage] = []
        self.latest_camera_frame: Optional[str] = None
        self.audio_enabled: bool = True
        self.camera_enabled: bool = True
        self.subtitle_enabled: bool = True
        self._processing_lock = asyncio.Lock()

    def handle_ping(self) -> PongMessage:
        return PongMessage()

    def toggle_audio(self, enabled: bool) -> None:
        self.audio_enabled = enabled

    def toggle_camera(self, enabled: bool) -> None:
        self.camera_enabled = enabled

    def toggle_subtitle(self, enabled: bool) -> None:
        self.subtitle_enabled = enabled

    def process_camera_frame(self, base64_data: str) -> None:
        """Store the latest camera frame for LLM to use"""
        self.latest_camera_frame = base64_data

    async def process_audio_chunk(self, base64_data: str) -> AsyncGenerator[ServerMessage, None]:
        """Process audio chunk with ASR and run full pipeline"""
        if not self.audio_enabled:
            return

        # ASR recognition
        asr_result = await self.asr_service.recognize(base64_data)
        if not asr_result.success or not asr_result.text.strip():
            return

        # Yield transcript
        yield UserTranscriptMessage(text=asr_result.text)

        # Add to conversation
        self.conversation_history.append(ConversationMessage(
            id=f"{int(asyncio.get_event_loop().time() * 1000)}-user",
            role="user",
            text=asr_result.text,
            timestamp=int(asyncio.get_event_loop().time() * 1000)
        ))
        # Trim history to prevent infinite growth - keep max 50 messages
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]

        # Run LLM and yield streaming response
        async for msg in self._run_llm_pipeline():
            yield msg

    async def _run_llm_pipeline(self) -> AsyncGenerator[ServerMessage, None]:
        """Run the full LLM -> TTS pipeline"""
        async with self._processing_lock:
            # Prepare LLM messages with vision if we have a camera frame
            llm_messages = self._build_llm_messages()
            session_id = str(int(asyncio.get_event_loop().time() * 1000))

            yield ModelStartMessage(sessionId=session_id)

            # Collect full response
            full_response = ""

            # Stream LLM tokens
            # Use Volcano Coding if available, otherwise Doubao
            if settings.volcano_access_key:
                stream = self.volcano_coding.chat_stream(llm_messages)
            else:
                stream = self.doubao_llm.chat_stream(llm_messages)

            async for token in stream:
                full_response += token
                yield ModelTokenMessage(token=token)

            # Add to conversation
            self.conversation_history.append(ConversationMessage(
                id=f"{session_id}-model",
                role="model",
                text=full_response,
                timestamp=int(asyncio.get_event_loop().time() * 1000)
            ))

            # TTS synthesis
            if full_response.strip():
                tts_result = await self.tts_service.synthesize(full_response)
                if tts_result.success and tts_result.audio:
                    base64_audio = base64.b64encode(tts_result.audio).decode('utf-8')
                    yield ModelAudioMessage(data=base64_audio)

            yield ModelEndMessage()

    def _build_llm_messages(self) -> list[LLMMessage]:
        """Build LLM messages, adding latest camera frame if available"""
        messages = []

        # System prompt
        messages.append(LLMMessage(
            role="system",
            content="你是一个友好的AI助手，可以看到用户的摄像头画面并进行对话。请保持回答简洁自然。"
        ))

        # Add conversation history
        for msg in self.conversation_history[-10:]:  # Keep last 10 messages for context
            if msg.role == "user" and msg is self.conversation_history[-1] and self.latest_camera_frame:
                # Last user message has image context
                content = [
                    LLMContentPart(type="text", text=msg.text),
                    LLMContentPart(type="image", image=self.latest_camera_frame)
                ]
                messages.append(LLMMessage(role="user", content=content))
            else:
                messages.append(LLMMessage(role=msg.role, content=msg.text))

        return messages

    def get_conversation_history(self) -> list[ConversationMessage]:
        return self.conversation_history
