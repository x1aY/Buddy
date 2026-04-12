"""
Alibaba Cloud Real-time Speech Recognition (Streaming) Service
https://help.aliyun.com/document_detail/142183.html
"""
import json
import asyncio
import uuid
import websockets
from typing import Callable, Optional
from models.schemas import ASRResult
from utils.logger import get_logger
from .aliyun_token import getAliToken

logger = get_logger("streaming_asr")


class StreamingASRService:
    """
    Streaming ASR client for one user connection.
    Maintains a persistent WebSocket connection to Alibaba Cloud ASR service.
    """

    def __init__(self):
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.task_id: Optional[str] = None
        self._connected = False
        self._transcription_started = False  # We have sent StartTranscription
        self._transcription_confirmed = False  # Server has responded with TranscriptionStarted
        self._receive_task: Optional[asyncio.Task] = None
        self._on_partial: Optional[Callable[[str], None]] = None
        self._on_final: Optional[Callable[[str], None]] = None
        self._current_text = ""
        self._appkey: Optional[str] = None
        self._token: Optional[str] = None
        # Buffer audio chunks that arrive before transcription is confirmed
        self._pending_audio_buffer: list[bytes] = []

    def _generate_id(self) -> str:
        """Generate a random UUID for task/message id"""
        return str(uuid.uuid4()).replace('-', '')

    async def start(
        self,
        on_partial: Callable[[str], None],
        on_final: Callable[[str], None]
    ) -> None:
        """
        Start a new streaming ASR session.
        Establishes WebSocket connection but does NOT send StartTranscription yet.
        Call start_transcription() after first audio chunk arrives.
        Get fresh token from Aliyun_token each time (token expires).
        """
        # Get fresh credentials each time (token has expiration)
        self._appkey, self._token = await getAliToken()
        if not self._appkey or not self._token:
            logger.warning("ASR credentials not configured or failed to get token")
            return

        self._on_partial = on_partial
        self._on_final = on_final
        self._current_text = ""
        self._transcription_started = False
        self.task_id = self._generate_id()

        url = f"wss://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1?token={self._token}"

        try:
            self.websocket = await websockets.connect(url)
            self._connected = True

            # Start background receive task
            self._receive_task = asyncio.create_task(self._receive_loop())

            logger.info("streaming_asr_connection_ready", task_id=self.task_id)
        except Exception as e:
            logger.error("streaming_asr_start_failed", error=str(e))
            self._connected = False
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

    async def start_transcription(self) -> bool:
        """
        Send StartTranscription message to begin recognition.
        Call this when first audio chunk arrives to avoid idle timeout.
        Returns True if started successfully, False otherwise.
        """
        if not self._connected or not self.websocket or self._transcription_started:
            return False

        try:
            # Send start message - correct format according to Alibaba docs
            start_msg = {
                "header": {
                    "appkey": self._appkey,
                    "namespace": "SpeechTranscriber",
                    "name": "StartTranscription",
                    "task_id": self.task_id,
                    "message_id": self._generate_id()
                },
                "payload": {
                    "format": "pcm",
                    "sample_rate": 16000,
                    "enable_intermediate_result": True,
                    "enable_punctuation_prediction": True,
                    "enable_inverse_text_normalization": True
                }
            }
            await self.websocket.send(json.dumps(start_msg))
            self._transcription_started = True
            logger.info("transcription_started", task_id=self.task_id)
            return True
        except Exception as e:
            logger.error("transcription_start_failed", error=str(e))
            return False

    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send an audio chunk to the ASR service.
        According to Alibaba protocol, audio data is sent as binary frame directly.
        If transcription hasn't been confirmed by server yet, buffer the chunk.
        """
        if not self._connected or not self.websocket or not self._transcription_started:
            logger.warning("send_audio_chunk_skipped", connected=self._connected, started=self._transcription_started)
            return

        if not self._transcription_confirmed:
            # Buffer until server confirms transcription started
            self._pending_audio_buffer.append(audio_data)
            return

        try:
            logger.debug("sending_audio_chunk", bytes=len(audio_data))
            # Send audio data as binary frame - correct per protocol
            await self.websocket.send(audio_data)
        except Exception as e:
            logger.error("send_audio_chunk_failed", error=str(e))

    async def stop(self) -> ASRResult:
        """Stop the current ASR session and get final result."""
        if not self._connected or not self.websocket:
            return ASRResult(text="", success=False)

        try:
            # Send stop message - correct format
            stop_msg = {
                "header": {
                    "appkey": self._appkey,
                    "namespace": "SpeechTranscriber",
                    "name": "StopTranscription",
                    "task_id": self.task_id,
                    "message_id": self._generate_id()
                }
            }
            await self.websocket.send(json.dumps(stop_msg))

            # Give some time for final result
            await asyncio.sleep(0.5)

            # Cancel receive task
            if self._receive_task and not self._receive_task.done():
                self._receive_task.cancel()

            # Close connection
            await self.websocket.close()
            self._connected = False
            self._transcription_started = False
            self.websocket = None

            final_text = self._current_text.strip()
            logger.info("streaming_asr_stopped", final_length=len(final_text))
            return ASRResult(text=final_text, success=len(final_text) > 0)

        except Exception as e:
            logger.error("streaming_asr_stop_failed", error=str(e))
            self._connected = False
            return ASRResult(text=self._current_text.strip(), success=False)

    async def _receive_loop(self) -> None:
        """Background loop to receive messages from ASR service."""
        if not self.websocket:
            return

        try:
            while self._connected:
                message = await self.websocket.recv()
                if isinstance(message, bytes):
                    logger.warning("received_binary_message", bytes=len(message))
                    continue  # should not happen

                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.error("invalid_json_from_asr", message_preview=message[:200])
                    continue

                # Get message name
                msg_name = data.get("header", {}).get("name")
                logger.debug("received_asr_message", msg_name=msg_name, full_data=data)

                # Handle different message types according to Alibaba protocol
                if msg_name == "TranscriptionStarted":
                    logger.debug("asr_transcription_started", task_id=self.task_id)
                    self._transcription_confirmed = True
                    # Send all buffered audio chunks now
                    if self._pending_audio_buffer and self.websocket:
                        for chunk in self._pending_audio_buffer:
                            await self.websocket.send(chunk)
                        self._pending_audio_buffer.clear()

                elif "payload" in data and "result" in data["payload"]:
                    result = data["payload"]["result"]
                    self._current_text = result

                    if msg_name == "TranscriptionResultChanged":
                        # Intermediate/partial result - update display immediately
                        logger.debug("transcription_result_changed", result=result)
                        if self._on_partial:
                            self._on_partial(result)
                    elif msg_name == "SentenceEnd":
                        # End of sentence - this is the final result for this sentence
                        logger.debug("sentence_end", result=result)
                        if self._on_final:
                            self._on_final(result)
                    elif msg_name == "TranscriptionCompleted":
                        # Complete transcription finished
                        logger.debug("transcription_completed", task_id=self.task_id, final_length=len(result))

        except asyncio.CancelledError:
            # Normal cancellation
            pass
        except Exception as e:
            logger.error("receive_loop_error", error=str(e))

    def is_transcription_started(self) -> bool:
        """Check if transcription has been started."""
        return self._transcription_started

    def get_current_text(self) -> str:
        """Get the current accumulated recognition text."""
        return self._current_text

    async def close(self) -> None:
        """Close the connection completely."""
        self._connected = False
        self._transcription_started = False
        self._transcription_confirmed = False
        self._pending_audio_buffer.clear()
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
