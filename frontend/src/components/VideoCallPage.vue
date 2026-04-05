<template>
  <div class="min-h-screen w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl"></div>
      <div
        class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-bg-float"
      ></div>
    </div>

    <!-- 摄像头预览 - 铺满整个背景 -->
    <transition name="fade">
      <div v-if="cameraEnabled" class="absolute inset-0 z-0">
        <CameraPreview :stream="cameraStream" />
      </div>
    </transition>

    <!-- 角落按钮 -->
    <!-- 左上角：字幕开关 -->
    <div class="absolute top-4 left-4 z-20">
      <button
        @click="toggleSubtitle"
        class="bg-black/60 hover:bg-black/70 text-white px-5 py-3 rounded-full font-medium transition-all duration-200 flex items-center gap-2 backdrop-blur-md"
      >
        <Subtitles class="w-5 h-5" />
        字幕
      </button>
    </div>

    <!-- 右上角：退出登录 -->
    <div class="absolute top-4 right-4 z-20">
      <button
        @click="handleLogout"
        class="bg-red-600/95 hover:bg-red-700 text-white px-5 py-3 rounded-full font-medium transition-all duration-200 flex items-center gap-2 backdrop-blur-md"
      >
        <LogOut class="w-5 h-5" />
        退出登录
      </button>
    </div>

    <!-- 对话内容区域 - 铺满主体 (仅当字幕开启时显示) -->
    <div
      v-if="isSubtitleEnabled"
      class="absolute inset-[100px_16px_110px_16px] bg-black/5 rounded-2xl backdrop-blur-sm z-10 flex flex-col"
    >
      <!-- 对话历史 - 可滚动 -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4">
        <div class="flex flex-col gap-3">
          <div
            v-for="message in conversationMessages"
            :key="message.id"
            :class="[
              'max-w-[70%]',
              message.role === 'model' ? 'self-start' : 'self-end'
            ]"
          >
            <div
              :class="[
                'px-4 py-3 rounded-2xl',
                message.role === 'model'
                  ? 'bg-blue-500/30 text-white rounded-tl-sm'
                  : 'bg-green-500/30 text-white rounded-tr-sm'
              ]"
            >
              {{ message.text }}
            </div>
          </div>
        </div>
      </div>

      <!-- 状态提示条 -->
      <div class="p-3">
        <div class="py-2 px-4 text-center text-white/90">
          {{ statusText }}
        </div>
      </div>
    </div>

    <!-- 底部控制栏 -->
    <div class="absolute bottom-6 left-6 right-6 z-20 flex items-center gap-3">
      <!-- 麦克风按钮 -->
      <button
        @click="toggleAudio"
        :class="[
          'w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-[1.05] active:scale-[0.95] backdrop-blur-md',
          isAudioEnabled
            ? 'bg-green-600/95 text-white'
            : 'bg-gray-700/95 text-gray-200'
        ]"
      >
        <Mic v-if="isAudioEnabled" class="w-6 h-6" />
        <MicOff v-else class="w-6 h-6" />
      </button>

      <!-- 输入框 -->
      <div class="flex-1">
        <input
          v-model="userInputText"
          @keyup.enter="sendUserInput"
          placeholder="输入对话..."
          class="w-full bg-white/92 text-gray-800 px-5 py-3 rounded-full outline-none placeholder:text-gray-500 backdrop-blur-md"
        />
      </div>

      <!-- 发送按钮 -->
      <button
        @click="sendUserInput"
        class="bg-blue-600/95 hover:bg-blue-700 text-white px-5 py-3 rounded-full font-medium transition-all duration-200 backdrop-blur-md"
      >
        发送
      </button>

      <!-- 摄像头按钮 -->
      <button
        @click="toggleCamera"
        :class="[
          'w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-[1.05] active:scale-[0.95] backdrop-blur-md',
          cameraEnabled
            ? 'bg-blue-600/95 text-white'
            : 'bg-gray-700/95 text-gray-200'
        ]"
      >
        <Video v-if="cameraEnabled" class="w-6 h-6" />
        <VideoOff v-else class="w-6 h-6" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useWebSocketClient } from '@/composables/use-websocket-client';
import { useAudioCapture } from '@/composables/use-audio-capture';
import { useCameraCapture } from '@/composables/use-camera-capture';
import { ConversationMessage, ServerMessage } from '@seeworldweb/shared/src/types';
import { DEFAULT_SUBTITLE_ENABLED } from '@seeworldweb/shared/src/constants';
import { Mic, MicOff, Video, VideoOff, LogOut, Subtitles } from 'lucide-vue-next';
import CameraPreview from './CameraPreview.vue';

const authStore = useAuthStore();
const router = useRouter();
const token = authStore.token;

// State
const isSubtitleEnabled = ref(DEFAULT_SUBTITLE_ENABLED);
const conversationMessages = ref<ConversationMessage[]>([]);
const currentModelMessage = ref('');
const isPlayingAudio = ref(false);
const userInputText = ref('');
const messagesContainer = ref<HTMLDivElement | null>(null);

// Track if there's an ongoing transcript (updated when messages change)
const hasOngoingTranscript = computed(() => {
  return conversationMessages.value.some(
    m => m.role === 'user' && Date.now() - m.timestamp < 2000
  );
});

// Auto-scroll to bottom when messages change
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

watch(() => conversationMessages.value.length, scrollToBottom);

// 计算状态提示文字
const statusText = computed(() => {
  if (!isConnected.value) {
    return '未连接';
  }

  if (conversationMessages.value.length === 0 && !isAudioEnabled.value) {
    return '问问我';
  }

  // If we have any ongoing user message being transcribed, we're listening
  if (hasOngoingTranscript.value && isAudioEnabled.value) {
    return '正在听';
  }

  // If currentModelMessage is being built, we're thinking/generating
  if (currentModelMessage.value && conversationMessages.value.length > 0 &&
      conversationMessages.value[conversationMessages.value.length - 1].role === 'model') {
    if (currentModelMessage.value !== conversationMessages.value[conversationMessages.value.length - 1].text) {
      return '正在生成回复';
    }
  } else if (currentModelMessage.value) {
    return '思考中';
  }

  if (isPlayingAudio.value) {
    return '正在生成回复';
  }

  // Default
  return '问问我';
});

// Composables
const { isConnected, connect, send, onMessage } = useWebSocketClient(token);

const { toggle: originalCameraToggle, isEnabled: cameraEnabled, getVideoStream } = useCameraCapture((frame) => {
  send({
    type: 'camera_frame',
    data: frame
  });
});

const { toggle: audioToggle, isEnabled: isAudioEnabled } = useAudioCapture((chunk) => {
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
  connect();
  onMessage(handleServerMessage);
  // Initialize camera stream if enabled
  if (cameraEnabled.value) {
    cameraStream.value = getVideoStream();
  }
});

function handleServerMessage(message: ServerMessage) {
  switch (message.type) {
    case 'user_transcript_ongoing':
      // Real-time update of ongoing segment in conversation list
      const { message_id, text } = message;
      // Find if this segment already exists
      const existingIndex = conversationMessages.value.findIndex(
        m => m.id === message_id
      );
      if (existingIndex >= 0) {
        // Update existing bubble
        conversationMessages.value[existingIndex].text = text;
      } else {
        // Add new bubble for new segment
        conversationMessages.value.push({
          id: message_id,
          role: 'user',
          text: text,
          timestamp: Date.now()
        });
      }
      break;

    case 'user_transcript_segment_end':
      // Nothing to do - segment already ended, next will be new bubble
      break;

    case 'user_transcript_partial':
      // Deprecated - keep for backward compatibility temporarily
      break;

    case 'user_transcript':
      // Final user transcript - add to conversation
      if (message.text === undefined) {
        break;
      }
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
      currentModelMessage.value += message.token!;
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
      if (message.data === undefined) {
        break;
      }
      playAudio(message.data);
      isPlayingAudio.value = true;
      break;

    case 'pong':
      // Just ignore, ping-pong keeps connection alive
      break;

    case 'error':
      console.error('Server error:', message.message);
      break;
  }
}

// Reuse single Audio instance for TTS playback
const audioPlayer = new Audio();

function playAudio(base64Audio: string) {
  audioPlayer.src = `data:audio/mp3;base64,${base64Audio}`;
  audioPlayer.play().catch(err => {
    console.error('Failed to play audio', err);
  });
  // When audio ends, go back to listening
  audioPlayer.onended = () => {
    isPlayingAudio.value = false;
  };
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
  isSubtitleEnabled.value = !isSubtitleEnabled.value;
  send({
    type: 'toggle_subtitle',
    enabled: isSubtitleEnabled.value
  });
}

function sendUserInput() {
  const text = userInputText.value.trim();
  if (!text) return;

  conversationMessages.value.push({
    id: Date.now().toString() + '-user',
    role: 'user',
    text: text,
    timestamp: Date.now()
  });
  currentModelMessage.value = '';

  send({
    type: 'user_transcript',
    text: text
  });

  userInputText.value = '';
}

function handleLogout() {
  authStore.logout();
  router.push('/login');
}
</script>

<style>
@keyframes bgFloat {
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(50px, 30px);
  }
}

.animate-bg-float {
  animation: bgFloat 8s infinite ease-in-out;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
