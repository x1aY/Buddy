<template>
  <div class="video-call-page full-screen flex-column">
    <!-- Camera Preview (when enabled) -->
    <CameraPreview v-if="cameraEnabled" :stream="cameraStream" />

    <!-- Main content container -->
    <div class="main-container" :class="{ 'camera-on': cameraEnabled }">
      <!-- Top bar with subtitle toggle -->
      <div class="top-bar">
        <SubtitleToggle
          :enabled="subtitleEnabled"
          @toggle="toggleSubtitle"
        />
      </div>

      <!-- Center area: robot icon or nothing when subtitle enabled -->
      <div class="center-area flex-center">
        <div v-if="!subtitleEnabled" class="robot-container">
          <img src="/robot-icon.svg" alt="Robot" class="robot-icon" />
          <p v-if="!isConnected" class="connecting-text">连接中...</p>
          <p v-if="isConnected && !audioEnabled" class="hint-text">点击左下角麦克风开始对话</p>
        </div>

        <!-- Subtitle display -->
        <SubtitleDisplay
          v-if="subtitleEnabled"
          :messages="conversationMessages"
          :cameraEnabled="cameraEnabled"
        />
      </div>

      <!-- Bottom control bar -->
      <div class="bottom-bar flex-center">
        <AudioToggle
          :enabled="audioEnabled"
          @toggle="toggleAudio"
        />
        <CameraToggle
          :enabled="cameraEnabled"
          @toggle="toggleCamera"
        />
        <button class="logout-btn" @click="handleLogout">
          🚪 退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useWebSocketClient } from '@/composables/use-websocket-client';
import { useAudioCapture } from '@/composables/use-audio-capture';
import { useCameraCapture } from '@/composables/use-camera-capture';
import AudioToggle from './AudioToggle.vue';
import CameraToggle from './CameraToggle.vue';
import SubtitleToggle from './SubtitleToggle.vue';
import SubtitleDisplay from './SubtitleDisplay.vue';
import CameraPreview from './CameraPreview.vue';
import { ConversationMessage, ServerMessage } from '@seeworldweb/shared/src/types';
import {
  DEFAULT_SUBTITLE_ENABLED
} from '@seeworldweb/shared/src/constants';

const authStore = useAuthStore();
const router = useRouter();
const token = authStore.token;

// State
const subtitleEnabled = ref(DEFAULT_SUBTITLE_ENABLED);
const conversationMessages = ref<ConversationMessage[]>([]);
const currentModelMessage = ref('');

// Composables
const { isConnected, connect, send, onMessage } = useWebSocketClient(token);

const { toggle: originalCameraToggle, isEnabled: cameraEnabled, getVideoStream } = useCameraCapture((frame) => {
  send({
    type: 'camera_frame',
    data: frame
  });
});

const { toggle: audioToggle, isEnabled: audioEnabled } = useAudioCapture((chunk) => {
  send({
    type: 'audio_chunk',
    data: chunk
  });
});

// Get camera stream for preview
const cameraStream = ref<MediaStream | null>(null);

// Wrap camera toggle to update stream reference
const cameraToggle = async () => {
  const newState = await originalCameraToggle();
  cameraStream.value = newState ? getVideoStream() : null;
  return newState;
};

onMounted(() => {
  // Connect WebSocket
  const socket = connect();
  onMessage(handleServerMessage);
  // Initialize camera stream if enabled
  if (cameraEnabled.value) {
    cameraStream.value = getVideoStream();
  }
});

function handleServerMessage(message: ServerMessage) {
  switch (message.type) {
    case 'user_transcript':
      conversationMessages.value.push({
        id: Date.now().toString() + '-user',
        role: 'user',
        text: message.text,
        timestamp: Date.now()
      });
      currentModelMessage.value = '';
      break;

    case 'model_start':
      currentModelMessage.value = '';
      break;

    case 'model_token':
      currentModelMessage.value += message.token;
      // Update last message if it's already a model message
      if (conversationMessages.value.length > 0 &&
          conversationMessages.value[conversationMessages.value.length - 1].role === 'model') {
        conversationMessages.value[conversationMessages.value.length - 1].text = currentModelMessage.value;
      } else {
        conversationMessages.value.push({
          id: Date.now().toString() + '-model',
          role: 'model',
          text: currentModelMessage.value,
          timestamp: Date.now()
        });
      }
      break;

    case 'model_audio':
      // Play audio
      playAudio(message.data);
      break;

    case 'pong':
      // Just ignore, ping-pong keeps connection alive
      break;

    case 'error':
      console.error('Server error:', message.message);
      break;
  }
}

function playAudio(base64Audio: string) {
  const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
  audio.play().catch(err => {
    console.error('Failed to play audio', err);
  });
}

async function toggleAudio() {
  const newState = await audioToggle();
  send({
    type: 'toggle_audio',
    enabled: newState
  });
}

async function toggleCamera() {
  const newState = await cameraToggle();
  cameraStream.value = newState ? getVideoStream() : null;
  send({
    type: 'toggle_camera',
    enabled: newState
  });
}

function toggleSubtitle() {
  subtitleEnabled.value = !subtitleEnabled.value;
  send({
    type: 'toggle_subtitle',
    enabled: subtitleEnabled.value
  });
}

function handleLogout() {
  authStore.logout();
  router.push('/login');
}
</script>

<style scoped>
.video-call-page {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  position: relative;
}

.main-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  z-index: 10;
  transition: all 0.3s ease;
}

.main-container.camera-on {
  background: transparent;
}

.top-bar {
  padding: 1rem;
  text-align: right;
}

.center-area {
  flex: 1;
  position: relative;
  overflow-y: auto;
}

.robot-container {
  text-align: center;
}

.robot-icon {
  width: 200px;
  height: 200px;
  opacity: 0.9;
  margin-bottom: 1rem;
}

.connecting-text, .hint-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1rem;
}

.bottom-bar {
  padding: 1.5rem;
  gap: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.logout-btn {
  padding: 1rem 1.5rem;
  border-radius: 50px;
  background: #dc3545;
  color: white;
  font-size: 1rem;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
}
</style>
