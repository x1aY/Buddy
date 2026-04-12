"""
ASR 流式处理 - 音频块接收，静音超时检测

This module handles streaming audio processing for Automatic Speech Recognition (ASR).
It manages the StreamingASRService connection, buffers incoming audio chunks, detects
silence timeouts, and triggers final result callback when silence is detected.
"""
import asyncio
import base64
from typing import Optional, Callable, List
from config import settings
from .providers.aliyun_streaming_asr import StreamingASRService
from utils.logger import get_logger

logger = get_logger("asr_stream_processor")


class AsrStreamProcessor:
    """
    Audio stream processor for continuous ASR with silence timeout detection.

    Responsibilities:
    - Manages StreamingASRService lifecycle (start/stop)
    - Buffers audio chunks received before ASR connection is ready
    - Tracks partial and final recognition results
    - Maintains silence timeout and triggers callback when timeout occurs
    - Provides access to current recognition text

    Args:
        on_final_result: Callback that will be invoked when silence is detected
            with the final recognized text.
        on_partial_result: Optional callback that will be invoked on partial
            recognition results for real-time display.
    """

    SILENCE_TIMEOUT_MS = 1500

    def __init__(
        self,
        on_final_result: Callable[[str], None],
        on_partial_result: Optional[Callable[[str, str], None]] = None
    ):
        self.on_final_result: Callable[[str], None] = on_final_result
        self.on_partial_result: Optional[Callable[[str, str], None]] = on_partial_result
        self.streaming_asr: Optional[StreamingASRService] = None

        # Buffer for audio chunks received before ASR is started
        self._pending_audio_buffer: List[bytes] = []

        # Current recognition segment state
        self._current_segment_id: Optional[str] = None
        self._current_segment_sentences: List[str] = []
        self._current_segment_ongoing: str = ""

        # Silence timer management
        self._silence_timer: Optional[asyncio.Task] = None
        self._silence_timer_id: int = 0
        self._silence_timeout_ms: int = self.SILENCE_TIMEOUT_MS

    def is_running(self) -> bool:
        """Check if ASR processing is currently running."""
        return self.streaming_asr is not None

    async def start(self) -> None:
        """
        Start ASR stream processing.

        If already running, stops the current session first.
        Initializes StreamingASRService and sets up callbacks for partial and final results.
        """
        if self.streaming_asr:
            await self.stop()

        self.streaming_asr = StreamingASRService()

        def on_partial(text: str) -> None:
            """
            Callback for partial (intermediate) recognition results.
            Updates the ongoing text and resets the silence timeout.
            """
            if not self.streaming_asr:
                return

            if self._current_segment_id is None:
                # Start a new recognition segment
                segment_id = str(int(asyncio.get_event_loop().time() * 1000))
                self._current_segment_id = segment_id
                self._current_segment_sentences.clear()
                self._current_segment_ongoing = text
            else:
                # Update existing segment with new partial result
                self._current_segment_ongoing = text

            # Cancel existing silence timer and start a new one
            if self._silence_timer:
                self._silence_timer.cancel()

            self._silence_timer_id += 1
            self._silence_timer = asyncio.create_task(
                self._silence_timeout_process(self._silence_timer_id)
            )

            # Send partial result to callback for real-time display
            if self.on_partial_result is not None:
                full_text = self.get_current_text()
                self.on_partial_result(self._current_segment_id, full_text)

        def on_final(final_text: str) -> None:
            """
            Callback for final recognition results (end of sentence).
            Adds the completed sentence to the sentence list.
            """
            if not self.streaming_asr:
                return
            if final_text.strip() and self._current_segment_id is not None:
                self._current_segment_sentences.append(final_text.strip())
                self._current_segment_ongoing = ""

        try:
            await self.streaming_asr.start(on_partial, on_final)
            logger.info("asr_stream_started", buffered_chunks=len(self._pending_audio_buffer))
        except Exception as e:
            logger.error("asr_stream_start_failed", error=str(e))
            await self.stop()
            raise

    async def process_audio_chunk(self, base64_data: str) -> None:
        """
        Process an incoming audio chunk in base64 format.

        If ASR is not running yet, buffers the chunk.
        If transcription hasn't started, attempts to start it and flushes buffered chunks.
        Otherwise, sends the chunk directly to the ASR service.

        Args:
            base64_data: Base64-encoded audio data (PCM format expected).
        """
        if not self.streaming_asr:
            # Buffer audio while waiting for ASR connection
            try:
                audio_data = base64.b64decode(base64_data)
                self._pending_audio_buffer.append(audio_data)
            except Exception as e:
                logger.error("process_audio_chunk_decode_failed", error=str(e))
            return

        try:
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
        except Exception as e:
            logger.error("process_audio_chunk_failed", error=str(e))
            # Don't stop on single chunk failure, just log it

    async def _silence_timeout_process(self, timer_id: int) -> None:
        """
        Background task that waits for silence timeout.

        When timeout occurs and this is still the active timer, it combines all recognized
        text, stops the ASR session, and triggers the final result callback.

        Args:
            timer_id: Unique identifier for this timer to detect outdated timers.
        """
        await asyncio.sleep(self._silence_timeout_ms / 1000)

        if timer_id != self._silence_timer_id:
            logger.info("silence_timeout_skip_outdated", timer_id=timer_id, active_id=self._silence_timer_id)
            return

        if not self.streaming_asr:
            logger.info("silence_timeout_skip_no_streaming_asr")
            return

        try:
            # Combine all recognized text
            final_parts: List[str] = []
            if self._current_segment_sentences:
                final_parts.extend(self._current_segment_sentences)
            if self._current_segment_ongoing.strip():
                final_parts.append(self._current_segment_ongoing.strip())

            final_text = " ".join(final_parts).strip()
            if not final_text:
                logger.info("silence_timeout_skip_empty_text")
                return

            logger.info("silence_timeout_final_text", length=len(final_text), text=final_text[:100])

            # Clear state
            self._current_segment_sentences.clear()
            self._current_segment_ongoing = ""
            self._current_segment_id = None
            self._silence_timer = None
            self._silence_timer_id = 0

            await self.stop()
            self.on_final_result(final_text)
        except Exception as e:
            logger.error("silence_timeout_process_failed", error=str(e))
            # Ensure cleanup even if processing fails
            try:
                await self.stop()
            except Exception as cleanup_e:
                logger.error("silence_timeout_cleanup_failed", error=str(cleanup_e))

    async def stop(self) -> None:
        """
        Stop ASR processing and clean up all resources.

        Cancels the silence timer, closes the ASR connection, and clears all state.
        """
        if self._silence_timer:
            self._silence_timer.cancel()
            self._silence_timer = None
            self._silence_timer_id = 0

        if self.streaming_asr:
            try:
                await self.streaming_asr.close()
            except Exception as e:
                logger.error("streaming_asr_close_failed", error=str(e))
            finally:
                self.streaming_asr = None

        self._pending_audio_buffer.clear()
        self._current_segment_id = None
        self._current_segment_sentences.clear()
        self._current_segment_ongoing = ""

    def get_current_text(self) -> str:
        """
        Get the combined current recognition text including both completed sentences
        and the ongoing partial result.

        Returns:
            Space-joined concatenated text.
        """
        parts: List[str] = []
        if self._current_segment_sentences:
            parts.extend(self._current_segment_sentences)
        if self._current_segment_ongoing.strip():
            parts.append(self._current_segment_ongoing.strip())
        return " ".join(parts).strip()
