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
from services import TTSService
from services.anthropic_llm import AnthropicLLMService
from services.openai_llm import OpenAILLMService
from services.streaming_asr import StreamingASRService
from utils.logger import get_logger

logger = get_logger("stream_processor")

# Singleton service instances - stateless, can be reused across connections
_tts_service = TTSService()
_anthropic_llm = AnthropicLLMService()
_openai_llm = OpenAILLMService()


class StreamProcessor:
    """Process incoming media stream and handle conversation"""

    # Silence timeout - if no audio for this many milliseconds, finish recognition

    def __init__(self):
        # Reuse singleton service instances
        self.tts_service = _tts_service
        self.anthropic_llm = _anthropic_llm
        self.openai_llm = _openai_llm
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
        self._silence_timeout_ms = 4000  # 4 seconds silence = end of speech (longer than segment timeout)
        # Buffer for audio chunks arrived before ASR connects
        self._pending_audio_buffer: list[bytes] = []

        # Streaming ASR segmentation - multiple bubble support
        # Each bubble = one segment, new bubble after silence timeout
        self._current_segment_id: Optional[str] = None
        self._current_segment_sentences: list[str] = []  # Sentences completed by ALiyun in current bubble
        self._current_segment_ongoing: str = ""          # Ongoing sentence in current bubble
        self._segment_silence_timer: Optional[asyncio.Task] = None
        self._segment_timeout_ms: int = 1500  # 1500ms = trigger LLM after 1.5s of silence
        self._finished_segments: list[str] = []  # Completed full segments (each is one bubble) - combined when LLM timeout triggers

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
        if not enabled:
            self.latest_camera_frame = None

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

            ALiyun ASR clears text after SentenceEnd, so we accumulate the full
            text of current segment ourselves to avoid losing previous sentences.
            """
            if not self._result_callback:
                return
            # Ignore late callbacks if ASR already stopped
            if not self.streaming_asr:
                return

            if self._current_segment_id is None:
                # Start of new bubble
                segment_id = str(int(asyncio.get_event_loop().time() * 1000))
                self._current_segment_id = segment_id
                self._current_segment_sentences.clear()
                self._current_segment_ongoing = text
            else:
                segment_id = self._current_segment_id
                # ALiyun gives us updated text for the ongoing sentence
                self._current_segment_ongoing = text

            # Cancel existing timeout - we got new speech
            if self._segment_silence_timer:
                self._segment_silence_timer.cancel()

            # Combine all completed sentences + current ongoing for frontend display
            full_current_text = " ".join(
                self._current_segment_sentences + [self._current_segment_ongoing]
            ).strip()

            # Schedule new segment timeout
            self._segment_silence_timer = asyncio.create_task(
                self._segment_silence_timeout(segment_id, full_current_text)
            )

            # Send ongoing update to frontend for real-time display
            if self._result_callback:
                self._result_callback(UserTranscriptOngoingMessage(
                    message_id=segment_id,
                    text=full_current_text
                ))

        # Only establish connection, don't send StartTranscription yet
        # StartTranscription will be sent when first audio chunk arrives
        await self.streaming_asr.start(on_partial, self._on_final_result)
        logger.info("streaming_asr_session_started", buffered_chunks=len(self._pending_audio_buffer))

    def _on_final_result(self, final_text: str) -> None:
        """Called when ALiyun ASR detects a SentenceEnd.
        ALiyun clears buffer after SentenceEnd, so we save the completed sentence
        to our current bubble before it disappears - we don't create a new bubble
        until our silence timeout triggers.
        """
        if not self.streaming_asr:
            return
        if final_text.strip() and self._current_segment_id is not None:
            self._current_segment_sentences.append(final_text.strip())

    async def _segment_silence_timeout(self, segment_id: str, final_text: str) -> None:
        """After silence timeout: finish current bubble, next speech starts new bubble."""
        await asyncio.sleep(self._segment_timeout_ms / 1000)

        # If this task was already canceled or we already have a new current segment, bail early
        # This prevents race conditions where new speech arrives before sleep completes
        # Also check if ASR is still active - if audio was toggled off/on, this is a stale task
        if not self.streaming_asr or self._current_segment_id != segment_id:
            logger.debug("segment_silence_timeout_stale_segment", expected=segment_id, current=self._current_segment_id)
            return

        if final_text.strip():
            self._finished_segments.append(final_text.strip())

        if self._result_callback:
            self._result_callback(UserTranscriptSegmentEndMessage(
                message_id=segment_id
            ))

        self._current_segment_id = None
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""

        # If we have finished segments and silence is detected, trigger LLM processing
        # This handles the case where each bubble is a complete question
        if len(self._finished_segments) > 0 and self.streaming_asr is not None:
            logger.info("segment_silence_trigger_llm_processing", segments=len(self._finished_segments))
            # Check if LLM is already processing (avoid concurrent processing)
            if self._processing_lock.locked():
                logger.info("segment_silence_skip_already_processing")
                return
            # Combine all finished segments and process immediately
            final_parts = self._finished_segments.copy()
            # Clear immediately after copying - prevent duplication if exception occurs later
            self._finished_segments.clear()
            current_text = ""
            if self.streaming_asr:
                current_text = self.streaming_asr.get_current_text().strip()
                if current_text:
                    final_parts.append(current_text)
            final_text = " ".join(final_parts).strip()
            if final_text and self._result_callback:
                logger.info("segment_silence_processing_final_text", length=len(final_text))
                # We are already in the segment timeout task - clear reference so _stop_streaming_asr doesn't cancel us
                self._segment_silence_timer = None
                # Stop streaming ASR before processing
                await self._stop_streaming_asr()
                # Do NOT send UserTranscriptMessage again - text already displayed via user_transcript_ongoing
                # Process with LLM
                async for msg in self.process_final_transcript(final_text):
                    self._result_callback(msg)
                await self._restart_asr_if_enabled()

    async def _silence_timeout_process(self) -> None:
        """Called after silence timeout - process final result"""
        logger.info("silence_timeout_triggered")
        await asyncio.sleep(self._silence_timeout_ms / 1000)

        if not self.streaming_asr:
            logger.info("silence_timeout_skip_no_streaming_asr")
            return

        # If we already have processed segments via segment_silence_timeout,
        # _finished_segments will be empty - no need to process again
        if len(self._finished_segments) == 0 and self._current_segment_id is None:
            logger.info("silence_timeout_skip_already_processed")
            return

        # Combine all finished segments + any current ongoing segment
        final_parts = self._finished_segments.copy()
        # Clear immediately after copying - prevent duplication if exception occurs later
        self._finished_segments.clear()
        logger.info("silence_timeout_segments", finished_count=len(final_parts))
        if self.streaming_asr:
            current_text = self.streaming_asr.get_current_text().strip()
            logger.info("silence_timeout_current_text", length=len(current_text), text=current_text[:100])
            if current_text:
                final_parts.append(current_text)

        final_text = " ".join(final_parts).strip()
        logger.info("silence_timeout_final_text", length=len(final_text), text=final_text[:100])
        if not final_text:
            logger.info("silence_timeout_skip_empty_text")
            return

        # Stop streaming ASR for this utterance
        await self._stop_streaming_asr()

        # Send final transcript
        if self._result_callback:
            self._result_callback(UserTranscriptMessage(text=final_text))

        # Process the final result with LLM and send all responses
        if self._result_callback:
            logger.info("starting_llm_processing", final_text_length=len(final_text))
            async for msg in self.process_final_transcript(final_text):
                self._result_callback(msg)
        await self._restart_asr_if_enabled()

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
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""

    async def _restart_asr_if_enabled(self) -> None:
        """Restart streaming ASR after LLM processing if audio is still enabled.
        This allows continuous conversation where user can keep speaking after AI responds.
        """
        if self.audio_enabled:
            await self._start_streaming_asr()

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
        logger.info("run_llm_pipeline_started")
        async with self._processing_lock:
            # Prepare LLM messages with vision if we have a camera frame
            llm_messages = self._build_llm_messages()
            session_id = str(int(asyncio.get_event_loop().time() * 1000))
            logger.info("llm_messages_built", count=len(llm_messages), session_id=session_id)

            yield ModelStartMessage(sessionId=session_id)

            # Collect full response
            full_response = ""

            # Stream LLM tokens
            # Priority: Anthropic protocol → OpenAI protocol
            if self.anthropic_llm.is_configured():
                logger.info("llm_selected", protocol="anthropic")
                stream = self.anthropic_llm.chat_stream(llm_messages)
            elif self.openai_llm.is_configured():
                logger.info("llm_selected", protocol="openai")
                stream = self.openai_llm.chat_stream(llm_messages)
            else:
                logger.error("no_llm_configured")
                yield ErrorMessage(message="No LLM service configured. Please set ANTHROPIC_AUTH_TOKEN or OPENAI_API_KEY in .env")
                return

            logger.info("llm_stream_started")
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
            # Map internal role name to LLMMessage allowed values
            role = msg.role
            if role == "model":
                role = "assistant"

            if msg.role == "user" and msg is self.conversation_history[-1] and self.latest_camera_frame:
                # Last user message has image context
                content = [
                    LLMContentPart(type="text", text=msg.text),
                    LLMContentPart(type="image", image=self.latest_camera_frame)
                ]
                messages.append(LLMMessage(role=role, content=content))
            else:
                messages.append(LLMMessage(role=role, content=msg.text))

        return messages

    def get_conversation_history(self) -> list[ConversationMessage]:
        return self.conversation_history
