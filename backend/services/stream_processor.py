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
    SILENCE_TIMEOUT_MS = 1500  # 1500ms = trigger LLM after 1.5s of silence (user finished speaking)

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
        # Buffer for audio chunks arrived before ASR connects
        self._pending_audio_buffer: list[bytes] = []

        # ASR keeps running continuously, single silence timeout after user stops speaking
        # All recognized text is accumulated and sent to LLM once after silence timeout
        # Still keeps multiple ongoing bubbles with real-time updates (蹦字 effect)
        self._current_segment_id: Optional[str] = None
        self._current_segment_sentences: list[str] = []  # Sentences completed by ALiyun in current segment
        self._current_segment_ongoing: str = ""          # Ongoing sentence in current segment
        self._silence_timer: Optional[asyncio.Task] = None
        self._silence_timer_id: int = 0  # Sequence number for current active timer
        self._silence_timeout_ms = self.SILENCE_TIMEOUT_MS

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

            # Cancel existing silence timeout - we got new speech, reset timer
            if self._silence_timer:
                self._silence_timer.cancel()

            # Combine all completed sentences + current ongoing for frontend display
            full_current_text = " ".join(
                self._current_segment_sentences + [self._current_segment_ongoing]
            ).strip()

            # Schedule new silence timeout - after silence timeout, trigger LLM processing
            self._silence_timer_id += 1
            self._silence_timer = asyncio.create_task(
                self._silence_timeout_process(self._silence_timer_id)
            )

            # Send ongoing update to frontend for real-time display (keeps蹦字 effect)
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
            # Clear ongoing after sentence end is finalized to avoid duplication
            # Next sentence will start fresh in ongoing
            self._current_segment_ongoing = ""


    async def _silence_timeout_process(self, timer_id: int) -> None:
        """Called after silence timeout - process final result"""
        await asyncio.sleep(self._silence_timeout_ms / 1000)

        # After sleep, check if this timer is still the active one
        # Multiple timers can be created due to continuous audio input, only the last one should proceed
        if timer_id != self._silence_timer_id:
            # This timer is outdated, skip
            logger.info("silence_timeout_skip_outdated", timer_id=timer_id, active_id=self._silence_timer_id)
            return

        logger.info("silence_timeout_triggered", timer_id=timer_id)

        if not self.streaming_asr:
            logger.info("silence_timeout_skip_no_streaming_asr")
            return

        # Combine all completed sentences + current ongoing segment
        final_parts: list[str] = []
        # Add all completed sentences from ASR
        if self._current_segment_sentences:
            final_parts.extend(self._current_segment_sentences)
        # Add current ongoing text
        if self._current_segment_ongoing.strip():
            final_parts.append(self._current_segment_ongoing.strip())

        final_text = " ".join(final_parts).strip()
        logger.info("silence_timeout_final_text", length=len(final_text), text=final_text[:100])
        if not final_text:
            logger.info("silence_timeout_skip_empty_text")
            return

        # Check if LLM is already processing (avoid concurrent processing)
        if self._processing_lock.locked():
            logger.info("silence_timeout_skip_already_processing")
            return

        # Clear segment state before stopping ASR - we've already combined the final text
        # This prevents _stop_streaming_asr from sending a duplicate UserTranscriptMessage
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""
        self._current_segment_id = None

        # Clear the silence timer reference before stopping ASR
        # We don't want _stop_streaming_asr to cancel us (the currently running timeout task)
        self._silence_timer = None
        self._silence_timer_id = 0

        # Stop streaming ASR for this utterance
        await self._stop_streaming_asr()

        # Send final transcript to frontend so it can save to backend
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
        # Before stopping, process any completed sentences and ongoing text
        # This handles case where user manually toggles off microphone before timeout
        # Collect text first, CLEAR STATE IMMEDIATELY to prevent duplicate sends if called again before we finish
        final_text: Optional[str] = None
        if self._result_callback and (self._current_segment_sentences or self._current_segment_ongoing.strip()):
            final_parts: list[str] = []
            # Add all completed sentences
            if self._current_segment_sentences:
                final_parts.extend(self._current_segment_sentences)
            # Add current ongoing text
            # Priority: use our accumulated ongoing text first (already synced with ASR callbacks)
            # Only fall back to ASR get_current_text if our accumulated is empty
            current_text = self._current_segment_ongoing.strip()
            if not current_text and self.streaming_asr:
                current_text = self.streaming_asr.get_current_text().strip()
            if current_text:
                final_parts.append(current_text)
            final_text = " ".join(final_parts).strip()

        # Clear segment state immediately after collecting - prevents duplicate sends
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
            self._silence_timer_id = 0
        if self.streaming_asr:
            await self.streaming_asr.close()
            self.streaming_asr = None
        # Clear pending buffer and segment state for next connection
        self._pending_audio_buffer.clear()
        self._current_segment_id = None
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""

        # Now send after state is cleared - if _stop_streaming_asr is called again concurrently,
        # state is already empty so no duplicate messages will be sent
        if final_text and self._result_callback:
            # Send final transcript to frontend
            self._result_callback(UserTranscriptMessage(text=final_text))
            # Process with LLM - just like silence timeout after manual stop
            logger.info("starting_llm_processing_manual_stop", final_text_length=len(final_text))
            asyncio.create_task(self._process_final_after_manual_stop(final_text))

    async def _process_final_after_manual_stop(self, final_text: str) -> None:
        """Process final transcript after manual microphone stop.
        Similar to what happens after silence timeout.
        """
        # Already holding processing lock? Wait for it
        async with self._processing_lock:
            # Process the final result with LLM and send all responses
            async for msg in self.process_final_transcript(final_text):
                if self._result_callback:
                    self._result_callback(msg)
        # Restart ASR if audio is still enabled
        await self._restart_asr_if_enabled()

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
            # Log all messages that will be sent to LLM
            for i, msg in enumerate(llm_messages):
                if isinstance(msg.content, list):
                    # Has image content, just log text part
                    text_parts = [part["text"] for part in msg.content if part["type"] == "text"]
                    logger.info("llm_message", index=i, role=msg.role, content=" ".join(text_parts)[:500])
                else:
                    logger.info("llm_message", index=i, role=msg.role, content=str(msg.content)[:500])

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
