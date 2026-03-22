import json
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query
from utils.jwt import verify_jwt_token
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

            if msg_type == "ping":
                await send_message(websocket, PongMessage())

            elif msg_type == "audio_chunk":
                msg = AudioChunkMessage(**msg_dict)
                async for response in processor.process_audio_chunk(msg.data):
                    await send_message(websocket, response)

            elif msg_type == "camera_frame":
                msg = CameraFrameMessage(**msg_dict)
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
