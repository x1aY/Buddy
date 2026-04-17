// ==================== WebSocket Message Types ====================

// Client -> Server messages
export type ClientMessage =
  | { type: 'audio_chunk'; data: string } // base64 encoded audio
  | { type: 'camera_frame'; data: string } // base64 encoded jpeg image
  | { type: 'toggle_audio'; enabled: boolean }
  | { type: 'toggle_camera'; enabled: boolean }
  | { type: 'toggle_subtitle'; enabled: boolean }
  | { type: 'user_transcript'; text: string } // text input from user
  | { type: 'set_conversation'; conversation_id: string } // set current active conversation
  | { type: 'ping' };

// Server -> Client messages
export type ServerMessage =
  | { type: 'user_transcript'; text: string } // ASR final result for user
  | { type: 'user_transcript_partial'; text: string } // Partial ASR result (streaming) - deprecated
  | { type: 'user_transcript_ongoing'; message_id: string; text: string } // Ongoing ASR segment (streaming bubble)
  | { type: 'user_transcript_segment_end'; message_id: string } // ASR segment finished
  | { type: 'model_start'; sessionId: string } // Model starts responding
  | { type: 'model_token'; token: string } // Streaming token from model
  | { type: 'model_audio'; data: string } // base64 encoded TTS audio
  | { type: 'model_end' } // Model finished responding
  | { type: 'conversation_title_updated'; title: string } // Conversation title updated
  | { type: 'pong' }
  | { type: 'error'; message: string };

// ==================== Conversation Types ====================

export interface ConversationMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: number;
}

// ==================== Authentication Types ====================

export interface UserInfo {
  id: string;
  name: string;
  avatar?: string;
  provider: 'huawei' | 'wechat';
}

export interface JwtPayload {
  userId: string;
  userName: string;
  provider: 'huawei' | 'wechat';
  iat: number;
  exp: number;
}

// ==================== API Response Types ====================

export interface LoginResponse {
  token: string;
  user: UserInfo;
}

export interface ErrorResponse {
  error: string;
  message: string;
}

// ==================== LLM Types ====================

export interface LLMMessage {
  role: 'user' | 'assistant' | 'system';
  content: string | LLMContentPart[];
}

export interface LLMContentPart {
  type: 'text' | 'image';
  text?: string;
  image?: string; // base64
}

export interface LLMCompletionRequest {
  messages: LLMMessage[];
  stream?: boolean;
}

// ==================== ASR Types ====================

export interface ASRResult {
  text: string;
  success: boolean;
}

// ==================== TTS Types ====================

export interface TTSResult {
  audio: Buffer;
  success: boolean;
}
