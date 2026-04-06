// UI Default States
export const DEFAULT_AUDIO_ENABLED = false;
export const DEFAULT_CAMERA_ENABLED = false;
export const DEFAULT_SUBTITLE_ENABLED = true;

// Camera Capture Settings
export const CAMERA_FRAME_INTERVAL_MS = 1000; // Send one frame per second
export const CAMERA_FRAME_QUALITY = 0.8; // JPEG quality
export const CAMERA_FRAME_MAX_WIDTH = 1280; // Max width for captured frame

// Audio Capture Settings
export const AUDIO_CHUNK_INTERVAL_MS = 100; // Audio chunk interval in ms
export const AUDIO_MIME_TYPE = 'audio/webm; codecs=opus';

// Subtitle Opacity when camera is active
export const SUBTITLE_OPACITY_WITH_CAMERA = 0.3;

// WebSocket Settings
export const WEBSOCKET_RECONNECT_DELAY_MS = 3000;
export const WEBSOCKET_PING_INTERVAL_MS = 30000;

// LLM Settings
export const LLM_MAX_HISTORY = 20; // Keep last 20 messages in conversation
