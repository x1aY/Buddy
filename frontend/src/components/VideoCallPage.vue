<template>
  <div class="min-h-screen w-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl"></div>
      <div
        class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-bg-float"
      ></div>
    </div>

    <!-- 摄像头预览 -->
    <transition name="fade">
      <CameraPreview v-if="cameraEnabled" :stream="cameraStream" />
    </transition>

    <!-- 主内容区 -->
    <div class="relative z-10 h-screen flex flex-col">
      <!-- 字幕开关按钮 -->
      <div class="absolute top-6 right-6">
        <button
          @click="toggleSubtitle"
          :class="[
            'btn-toggle-sm',
            isSubtitleEnabled
              ? 'bg-amber-500 text-white'
              : 'btn-toggle-inactive'
          ]"
        >
          <Subtitles class="w-5 h-5" />
          字幕{{ isSubtitleEnabled ? '开启' : '关闭' }}
        </button>
      </div>

      <!-- 中心内容区域 -->
      <div class="flex-1 flex items-start justify-center p-6 pt-16">
        <transition mode="out-in">
          <!-- AI悬浮球 -->
          <div
            v-if="!isSubtitleEnabled"
            key="orb"
            class="text-center flex flex-col items-center justify-center h-full"
          >
            <AIOrb :state="aiOrbState" />
            <p
              class="mt-16 text-lg"
              :class="cameraEnabled ? 'text-white/90' : 'text-gray-400'"
            >
              点击麦克风开始对话
            </p>
          </div>

          <!-- 对话字幕区域 -->
          <div
            v-else
            key="subtitles"
            class="w-full max-w-4xl max-h-[60vh] overflow-y-auto px-4"
          >
            <SubtitleDisplay
              :messages="conversationMessages"
              :camera-enabled="cameraEnabled"
              :partial-text="partialUserTranscript"
            />
          </div>
        </transition>
      </div>

      <!-- 底部控制栏 -->
      <div class="p-6 flex justify-center items-center gap-4">
        <!-- 麦克风按钮 -->
        <button
          @click="toggleAudio"
          :class="[
            'px-8 py-4 rounded-full font-medium shadow-xl transition-all duration-200 flex items-center gap-3 hover:scale-[1.05] active:scale-[0.95]',
            isAudioEnabled
              ? 'bg-green-500 text-white'
              : 'bg-gray-700/80 text-gray-300 backdrop-blur-sm'
          ]"
        >
          <Mic v-if="isAudioEnabled" class="w-5 h-5" />
          <MicOff v-else class="w-5 h-5" />
          声音{{ isAudioEnabled ? '开启' : '关闭' }}
        </button>

        <!-- 摄像头按钮 -->
        <button
          @click="toggleCamera"
          :class="[
            'px-8 py-4 rounded-full font-medium shadow-xl transition-all duration-200 flex items-center gap-3 hover:scale-[1.05] active:scale-[0.95]',
            cameraEnabled
              ? 'bg-blue-500 text-white'
              : 'bg-gray-700/80 text-gray-300 backdrop-blur-sm'
          ]"
        >
          <Video v-if="cameraEnabled" class="w-5 h-5" />
          <VideoOff v-else class="w-5 h-5" />
          摄像头{{ cameraEnabled ? '开启' : '关闭' }}
        </button>

        <!-- 退出登录按钮 -->
        <button
          @click="handleLogout"
          class="px-8 py-4 bg-red-600 hover:bg-red-700 text-white rounded-full font-medium shadow-xl transition-all duration-200 flex items-center gap-3 hover:scale-[1.05] active:scale-[0.95]"
        >
          <LogOut class="w-5 h-5" />
          退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useWebSocketClient } from '@/composables/use-websocket-client';
import { useAudioCapture } from '@/composables/use-audio-capture';
import { useCameraCapture } from '@/composables/use-camera-capture';
import { ConversationMessage, ServerMessage } from '@seeworldweb/shared/src/types';
import { DEFAULT_SUBTITLE_ENABLED } from '@seeworldweb/shared/src/constants';
import { Mic, MicOff, Video, VideoOff, LogOut, Subtitles } from 'lucide-vue-next';
import AIOrb from './AIOrb.vue';
import SubtitleDisplay from './SubtitleDisplay.vue';
import CameraPreview from './CameraPreview.vue';

type AIOrbState = "listening" | "thinking" | "speaking";

const authStore = useAuthStore();
const router = useRouter();
const token = authStore.token;

// State
const isSubtitleEnabled = ref(DEFAULT_SUBTITLE_ENABLED);
const conversationMessages = ref<ConversationMessage[]>([]);
const currentModelMessage = ref('');
const partialUserTranscript = ref('');
const isPlayingAudio = ref(false);

// Derived AI orb state based on current conversation status
const aiOrbState = computed<AIOrbState>(() => {
  if (!isAudioEnabled.value) {
    return "listening";
  }

  // If we have a partial transcript, we're listening
  if (partialUserTranscript.value) {
    return "listening";
  }

  // If we're playing audio, we're speaking
  if (isPlayingAudio.value) {
    return "speaking";
  }

  // If currentModelMessage is being built, we're thinking
  if (currentModelMessage.value && conversationMessages.value.length > 0 &&
      conversationMessages.value[conversationMessages.value.length - 1].role === 'model') {
    // Still getting tokens - thinking
    if (currentModelMessage.value !== conversationMessages.value[conversationMessages.value.length - 1].text) {
      return "thinking";
    } else {
      // Done generating, playing audio - speaking
      return "speaking";
    }
  } else if (currentModelMessage.value) {
    return "thinking";
  } else {
    return "listening";
  }
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
  const socket = connect();
  onMessage(handleServerMessage);
  // Initialize camera stream if enabled
  if (cameraEnabled.value) {
    cameraStream.value = getVideoStream();
  }
});

function handleServerMessage(message: ServerMessage) {
  switch (message.type) {
    case 'user_transcript_partial':
      // Real-time update of partial user transcript
      partialUserTranscript.value = message.text || '';
      break;

    case 'user_transcript':
      // Final user transcript - add to conversation, clear partial
      if (message.text === undefined) {
        break;
      }
      conversationMessages.value.push({
        id: Date.now().toString() + '-user',
        role: 'user',
        text: message.text,
        timestamp: Date.now()
      });
      partialUserTranscript.value = '';
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
