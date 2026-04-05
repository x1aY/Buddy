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
    UserTranscriptPartialMessage,
    UserTranscriptOngoingMessage,
    UserTranscriptSegmentEndMessage,
    ModelStartMessage,
    ModelTokenMessage,
    ModelAudioMessage,
    ModelEndMessage,
    PongMessage,
    ErrorMessage,
)
from services import TTSService, DoubaoLLMService, VolcanoCodingService
from services.streaming_asr import StreamingASRService
from utils.logger import get_logger

logger = get_logger("stream_processor")

# Singleton service instances - stateless, can be reused across connections
_tts_service = TTSService()
_doubao_llm = DoubaoLLMService()
_volcano_coding = VolcanoCodingService()


class StreamProcessor:
    """Process incoming media stream and handle conversation"""

    # Silence timeout - if no audio for this many milliseconds, finish recognition

    def __init__(self):
        # Reuse singleton service instances
        self.tts_service = _tts_service
        self.doubao_llm = _doubao_llm
        self.volcano_coding = _volcano_coding
        self.conversation_history: list[ConversationMessage] = []
        self.latest_camera_frame: Optional[str] = None
        self.audio_enabled: bool = True
        self.camera_enabled: bool = True
        self.subtitle_enabled: bool = True
        self._processing_lock = asyncio.Lock()
        self._result_callback: Optional[callable] = None

        # Streaming ASR
        self.streaming_asr: Optional[StreamingASRService] = None
        self._silence_timer: Optional[asyncio.Task] = None
        self._silence_timeout_ms = 2000  # 2 seconds silence = end of speech
        # Buffer for audio chunks arrived before ASR connects
        self._pending_audio_buffer: list[bytes] = []

        # Streaming ASR segmentation - for multiple bubbles
        self._current_segment_id: Optional[str] = None
        self._segment_silence_timer: Optional[asyncio.Task] = None
        self._segment_timeout_ms: int = 700  # Segment silence timeout (ms)
        self._finished_segments: list[str] = []  # Completed segment texts

    def handle_ping(self) -> PongMessage:
        return PongMessage()

    def toggle_audio(self, enabled: bool) -> None:
        """Toggle audio capture and reset streaming ASR"""
        self.audio_enabled = enabled
        if enabled:
            # When audio is enabled again, start fresh streaming ASR
            asyncio.create_task(self._start_streaming_asr())
        else:
            # When audio is disabled, stop any ongoing recognition
            asyncio.create_task(self._stop_streaming_asr())

    def toggle_camera(self, enabled: bool) -> None:
        self.camera_enabled = enabled

    def toggle_subtitle(self, enabled: bool) -> None:
        self.subtitle_enabled = enabled

    def process_camera_frame(self, base64_data: str) -> None:
        """Store the latest camera frame for LLM to use"""
        self.latest_camera_frame = base64_data

    async def process_audio_chunk(self, base64_data: str) -> AsyncGenerator[ServerMessage, None]:
        """Process audio chunk with streaming ASR.
        Partial results are sent immediately for real-time display.
        After silence timeout, final result is processed by LLM.
        """
        if not self.audio_enabled:
            return

        # Decode audio data
        audio_data = base64.b64decode(base64_data)

        if not self.streaming_asr:
            # Buffer audio chunks while ASR is connecting
            self._pending_audio_buffer.append(audio_data)
            return

        if not self.streaming_asr.is_transcription_started():
            # First audio chunk has arrived - start transcription now
            # This avoids IDLE_TIMEOUT because we send StartTranscription
            # and immediately start sending audio data, no idle time
            started = await self.streaming_asr.start_transcription()
            if started:
                # Send any buffered audio chunks that arrived before transcription started
                if self._pending_audio_buffer:
                    for chunk in self._pending_audio_buffer:
                        await self.streaming_asr.send_audio_chunk(chunk)
                    self._pending_audio_buffer.clear()

                # Send current audio chunk too
                await self.streaming_asr.send_audio_chunk(audio_data)
            # else: connection not ready yet, next chunk will retry
        else:
            # Transcription already started - send immediately
            await self.streaming_asr.send_audio_chunk(audio_data)

        # Reset the silence timer - if we don't get more audio for timeout, we stop
        if self._silence_timer:
            self._silence_timer.cancel()

        # Schedule a new timer - after timeout, process final result
        self._silence_timer = asyncio.create_task(self._silence_timeout_process())

        # Yield nothing now - partial results come from streaming ASR callbacks
        # The yield below ensures this is recognized as an async generator
        if False:
            yield

    async def _start_streaming_asr(self) -> None:
        """Start streaming ASR session"""
        if self.streaming_asr:
            await self._stop_streaming_asr()

        self.streaming_asr = StreamingASRService()

        def on_partial(text: str):
            """Called by streaming ASR when partial result available.
            Create new segment if none active, update text, send to frontend.
            """
            if not self._result_callback:
                return

            # Create new segment if none active
            if self._current_segment_id is None:
                segment_id = str(int(asyncio.get_event_loop().time() * 1000))
                self._current_segment_id = segment_id
            else:
                segment_id = self._current_segment_id

            # Reset segment silence timer
            if self._segment_silence_timer:
                self._segment_silence_timer.cancel()

            # Schedule new segment timeout
            self._segment_silence_timer = asyncio.create_task(
                self._segment_silence_timeout(segment_id, text)
            )

            # Send ongoing update to frontend for real-time display
            if self._result_callback:
                self._result_callback(UserTranscriptOngoingMessage(
                    message_id=segment_id,
                    text=text
                ))

        # Only establish connection, don't send StartTranscription yet
        # StartTranscription will be sent when first audio chunk arrives
        await self.streaming_asr.start(on_partial, self._on_final_result)
        logger.info("streaming_asr_session_started", buffered_chunks=len(self._pending_audio_buffer))

    def _on_final_result(self, final_text: str) -> None:
        """Called by streaming ASR when final result is available"""
        pass

    async def _segment_silence_timeout(self, segment_id: str, final_text: str) -> None:
        """Called after segment silence timeout - finish this segment.
        Next speech will start a new bubble.
        """
        await asyncio.sleep(self._segment_timeout_ms / 1000)

        # Save to finished segments
        if final_text.strip():
            self._finished_segments.append(final_text.strip())

        # Notify frontend segment ended
        if self._result_callback:
            self._result_callback(UserTranscriptSegmentEndMessage(
                message_id=segment_id
            ))

        # Clear current segment - next speech starts new bubble
        self._current_segment_id = None

    async def _silence_timeout_process(self) -> None:
        """Called after silence timeout - process final result"""
        await asyncio.sleep(self._silence_timeout_ms / 1000)

        if not self.streaming_asr:
            return

        # Combine all finished segments + any current ongoing segment
        final_parts = self._finished_segments.copy()
        if self.streaming_asr:
            current_text = self.streaming_asr.get_current_text().strip()
            if current_text:
                final_parts.append(current_text)

        final_text = " ".join(final_parts).strip()
        if not final_text:
            return

        # Stop streaming ASR for this utterance
        await self._stop_streaming_asr()

        # Send final transcript
        if self._result_callback:
            self._result_callback(UserTranscriptMessage(text=final_text))

        # Process the final result with LLM and send all responses
        if self._result_callback:
            async for msg in self.process_final_transcript(final_text):
                self._result_callback(msg)

    def set_result_callback(self, callback: callable) -> None:
        """Set callback to send ServerMessage to websocket"""
        self._result_callback = callback

    async def _stop_streaming_asr(self) -> None:
        """Stop current streaming ASR session"""
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
        if self._segment_silence_timer:
            self._segment_silence_timer.cancel()
            self._segment_silence_timer = None
        if self.streaming_asr:
            await self.streaming_asr.close()
            self.streaming_asr = None
        # Clear pending buffer and segment state for next connection
        self._pending_audio_buffer.clear()
        self._finished_segments.clear()
        self._current_segment_id = None

    async def process_final_transcript(self, text: str) -> AsyncGenerator[ServerMessage, None]:
        """Process final user transcript with LLM and TTS"""
        if not text.strip():
            return

        # Add to conversation
        self.conversation_history.append(ConversationMessage(
            id=f"{int(asyncio.get_event_loop().time() * 1000)}-user",
            role="user",
            text=text,
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
