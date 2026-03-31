from pydantic import BaseModel, Field
from typing import Optional, Union, List, Literal


# ==================== Authentication Types ====================

class UserInfo(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    provider: Literal['huawei', 'wechat']


class JwtPayload(BaseModel):
    userId: str
    userName: str
    provider: Literal['huawei', 'wechat']
    iat: int
    exp: int


class LoginResponse(BaseModel):
    token: str
    user: UserInfo


class ErrorResponse(BaseModel):
    error: str
    message: str


# ==================== WebSocket Message Types ====================

# Client -> Server messages
class AudioChunkMessage(BaseModel):
    type: Literal['audio_chunk'] = 'audio_chunk'
    data: str  # base64 encoded audio


class CameraFrameMessage(BaseModel):
    type: Literal['camera_frame'] = 'camera_frame'
    data: str  # base64 encoded jpeg image


class ToggleAudioMessage(BaseModel):
    type: Literal['toggle_audio'] = 'toggle_audio'
    enabled: bool


class ToggleCameraMessage(BaseModel):
    type: Literal['toggle_camera'] = 'toggle_camera'
    enabled: bool


class ToggleSubtitleMessage(BaseModel):
    type: Literal['toggle_subtitle'] = 'toggle_subtitle'
    enabled: bool


class PingMessage(BaseModel):
    type: Literal['ping'] = 'ping'


ClientMessage = Union[
    AudioChunkMessage,
    CameraFrameMessage,
    ToggleAudioMessage,
    ToggleCameraMessage,
    ToggleSubtitleMessage,
    PingMessage
]


# Server -> Client messages
class UserTranscriptMessage(BaseModel):
    type: Literal['user_transcript'] = 'user_transcript'
    text: str


class UserTranscriptPartialMessage(BaseModel):
    type: Literal['user_transcript_partial'] = 'user_transcript_partial'
    text: str  # 部分识别结果（流式更新）


class ModelStartMessage(BaseModel):
    type: Literal['model_start'] = 'model_start'
    sessionId: str


class ModelTokenMessage(BaseModel):
    type: Literal['model_token'] = 'model_token'
    token: str


class ModelAudioMessage(BaseModel):
    type: Literal['model_audio'] = 'model_audio'
    data: str  # base64 encoded TTS audio


class ModelEndMessage(BaseModel):
    type: Literal['model_end'] = 'model_end'


class PongMessage(BaseModel):
    type: Literal['pong'] = 'pong'


class ErrorMessage(BaseModel):
    type: Literal['error'] = 'error'
    message: str


ServerMessage = Union[
    UserTranscriptMessage,
    UserTranscriptPartialMessage,
    ModelStartMessage,
    ModelTokenMessage,
    ModelAudioMessage,
    ModelEndMessage,
    PongMessage,
    ErrorMessage
]


# ==================== Conversation Types ====================

class ConversationMessage(BaseModel):
    id: str
    role: Literal['user', 'model']
    text: str
    timestamp: int


# ==================== LLM Types ====================

class LLMContentPart(BaseModel):
    type: Literal['text', 'image']
    text: Optional[str] = None
    image: Optional[str] = None  # base64


class LLMMessage(BaseModel):
    role: Literal['user', 'assistant', 'system']
    content: Union[str, List[LLMContentPart]]


class LLMCompletionRequest(BaseModel):
    messages: List[LLMMessage]
    stream: Optional[bool] = True


# ==================== ASR Types ====================

class ASRResult(BaseModel):
    text: str
    success: bool


# ==================== TTS Types ====================

class TTSResult(BaseModel):
    audio: bytes
    success: bool
