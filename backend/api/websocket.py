import json
import time
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query
from utils.jwt import verify_jwt_token
from utils.logger import get_logger
from models.schemas import (
    ClientMessage,
    ServerMessage,
    PongMessage,
    ErrorMessage,
    AudioChunkMessage,
    CameraFrameMessage,
    ToggleAudioMessage,
    ToggleCameraMessage,
    ToggleSubtitleMessage,
    PingMessage
)
from services import StreamProcessor

logger = get_logger("websocket")


async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """WebSocket endpoint for media streaming"""
    await websocket.accept()

    # Authenticate - allow missing token for guest mode
    user_id: Optional[str] = None
    if token:
        payload = verify_jwt_token(token)
        if payload:
            user_id = payload.userId

    # If token is invalid, still allow guest connection
    # Guest mode is always allowed

    # Create stream processor for this connection
    processor = StreamProcessor()

    # Statistics for rate-limited logging
    stats = {
        'audio_chunks': 0,
        'camera_frames': 0,
        'total_audio_bytes': 0,
        'total_camera_bytes': 0,
        'last_log_time': 0
    }
    DATA_TRANSFER_LOG_INTERVAL = 60  # Log once per minute

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            try:
                msg_dict = json.loads(data)
            except json.JSONDecodeError:
                await send_message(websocket, ErrorMessage(message="Invalid JSON"))
                continue

            # Parse message based on type
            msg_type = msg_dict.get("type")
            current_time = int(time.time())

            if msg_type == "ping":
                await send_message(websocket, PongMessage())

            elif msg_type == "audio_chunk":
                msg = AudioChunkMessage(**msg_dict)
                stats['audio_chunks'] += 1
                stats['total_audio_bytes'] += len(msg.data)
                # Check if we need to log
                if current_time - stats['last_log_time'] >= DATA_TRANSFER_LOG_INTERVAL:
                    logger.info(
                        "data_transfer_stats",
                        audio_chunks=stats['audio_chunks'],
                        camera_frames=stats['camera_frames'],
                        total_audio_bytes=stats['total_audio_bytes'],
                        total_camera_bytes=stats['total_camera_bytes']
                    )
                    # Reset stats after logging
                    stats['audio_chunks'] = 0
                    stats['camera_frames'] = 0
                    stats['total_audio_bytes'] = 0
                    stats['total_camera_bytes'] = 0
                    stats['last_log_time'] = current_time
                async for response in processor.process_audio_chunk(msg.data):
                    await send_message(websocket, response)

            elif msg_type == "camera_frame":
                msg = CameraFrameMessage(**msg_dict)
                stats['camera_frames'] += 1
                stats['total_camera_bytes'] += len(msg.data)
                # Check if we need to log (same interval as audio)
                if current_time - stats['last_log_time'] >= DATA_TRANSFER_LOG_INTERVAL:
                    logger.info(
                        "data_transfer_stats",
                        audio_chunks=stats['audio_chunks'],
                        camera_frames=stats['camera_frames'],
                        total_audio_bytes=stats['total_audio_bytes'],
                        total_camera_bytes=stats['total_camera_bytes']
                    )
                    # Reset stats after logging
                    stats['audio_chunks'] = 0
                    stats['camera_frames'] = 0
                    stats['total_audio_bytes'] = 0
                    stats['total_camera_bytes'] = 0
                    stats['last_log_time'] = current_time
                processor.process_camera_frame(msg.data)

            elif msg_type == "toggle_audio":
                msg = ToggleAudioMessage(**msg_dict)
                processor.toggle_audio(msg.enabled)

            elif msg_type == "toggle_camera":
                msg = ToggleCameraMessage(**msg_dict)
                processor.toggle_camera(msg.enabled)

            elif msg_type == "toggle_subtitle":
                msg = ToggleSubtitleMessage(**msg_dict)
                processor.toggle_subtitle(msg.enabled)

            else:
                await send_message(websocket, ErrorMessage(message=f"Unknown message type: {msg_type}"))

    except WebSocketDisconnect:
        # Connection closed
        pass


async def send_message(websocket: WebSocket, message: ServerMessage) -> None:
    """Send a typed message to websocket"""
    json_str = json.dumps(message.model_dump(), ensure_ascii=False)
    await websocket.send_text(json_str)
