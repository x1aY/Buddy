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
        class="bg-white/10 hover:bg-white/20 text-white w-12 h-12 rounded-full font-medium transition-all duration-200 flex items-center justify-center backdrop-blur-md"
      >
        <Subtitles class="w-5 h-5" />
      </button>
    </div>

    <!-- 右上角：历史 + 退出登录 -->
    <div class="absolute top-4 right-4 z-20 flex items-center gap-3">
      <!-- 历史按钮 -->
      <div class="relative" ref="historyDropdownContainer">
        <button
          @click="toggleHistoryDropdown"
          class="bg-white/10 hover:bg-white/20 text-white w-12 h-12 rounded-full font-medium transition-all duration-200 flex items-center justify-center backdrop-blur-md relative"
        >
          <History class="w-5 h-5" />
          <span class="absolute bottom-1 right-1 text-xs opacity-80">▾</span>
        </button>

        <!-- 下拉菜单 -->
        <transition name="dropdown">
          <div
            v-if="historyDropdownOpen"
            class="absolute top-16 right-0 w-80 max-h-[450px] bg-slate-900/95 border border-slate-700 rounded-xl p-2 shadow-2xl overflow-hidden backdrop-blur-md"
          >
            <!-- 当前对话 -->
            <div
              v-if="currentConversationId"
              class="p-3 bg-blue-600 text-white rounded-lg mb-2"
            >
              <div class="flex justify-between items-center">
                <div>
                  <div class="flex items-center gap-2">
                    <span>●</span>
                    <span class="font-medium">当前对话</span>
                  </div>
                  <div
                    v-if="currentConversationTitle"
                    class="text-xs opacity-90 mt-1 whitespace-nowrap overflow-hidden text-ellipsis max-w-60"
                  >
                    {{ currentConversationTitle }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 分隔线 -->
            <div v-if="conversationList.length > 1" class="h-px bg-slate-700 my-2"></div>

            <!-- 历史对话列表 -->
            <div class="max-h-[280px] overflow-y-auto">
              <div
                v-for="conv in filteredConversationList"
                :key="conv.id"
                @click="switchConversation(conv.id)"
                class="flex items-start p-3 bg-slate-800 text-slate-200 rounded-lg mb-1.5 cursor-pointer hover:bg-slate-700 transition-colors"
              >
                <div class="flex-1 min-w-0">
                  <div class="flex justify-between items-center">
                    <span class="text-xs text-slate-400">{{ formatDate(conv.updated_at) }}</span>
                  </div>
                  <div
                    class="text-sm mt-1 whitespace-nowrap overflow-hidden text-ellipsis max-w-60"
                  >
                    {{ conv.title }}
                  </div>
                </div>
                <button
                  @click.stop="deleteConversation(conv.id)"
                  class="bg-transparent border-none text-red-500 px-2 py-1 rounded text-sm opacity-80 hover:opacity-100 ml-2"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- 分隔线 -->
            <div class="h-px bg-slate-700 my-2"></div>

            <!-- 新建对话按钮 -->
            <button
              @click="createNewConversation"
              class="w-full bg-emerald-600 hover:bg-emerald-700 text-white border-none py-3 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors"
            >
              <span>➕</span>
              <span>新建对话</span>
            </button>
          </div>
        </transition>
      </div>

      <!-- 退出登录 -->
      <button
        @click="handleLogout"
        class="bg-white/10 hover:bg-white/20 text-white w-12 h-12 rounded-full font-medium transition-all duration-200 flex items-center justify-center backdrop-blur-md"
      >
        <LogOut class="w-5 h-5" />
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
            ? 'bg-white/15 text-white'
            : 'bg-white/10 text-white'
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
        class="bg-white/10 hover:bg-white/20 text-white px-5 py-3 rounded-full font-medium transition-all duration-200 backdrop-blur-md"
      >
        发送
      </button>

      <!-- 摄像头按钮 -->
      <button
        @click="toggleCamera"
        :class="[
          'w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-[1.05] active:scale-[0.95] backdrop-blur-md',
          cameraEnabled
            ? 'bg-white/15 text-white'
            : 'bg-white/10 text-white'
        ]"
      >
        <Video v-if="cameraEnabled" class="w-6 h-6" />
        <VideoOff v-else class="w-6 h-6" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useWebSocketClient } from '@/composables/use-websocket-client';
import { useAudioCapture } from '@/composables/use-audio-capture';
import { useCameraCapture } from '@/composables/use-camera-capture';
import { ConversationMessage, ServerMessage } from '@seeworldweb/shared/src/types';
import { DEFAULT_SUBTITLE_ENABLED } from '@seeworldweb/shared/src/constants';
import { Mic, MicOff, Video, VideoOff, LogOut, Subtitles, History, Trash2 } from 'lucide-vue-next';
import * as ConversationApi from '@/api/conversations';
import type { ConversationItem } from '@/api/conversations';
import CameraPreview from './CameraPreview.vue';

const authStore = useAuthStore();
const token = authStore.token;

// State
const isSubtitleEnabled = ref(DEFAULT_SUBTITLE_ENABLED);
const conversationMessages = ref<ConversationMessage[]>([]);
const currentModelMessage = ref('');
const isPlayingAudio = ref(false);
const userInputText = ref('');
const messagesContainer = ref<HTMLDivElement | null>(null);

// Conversation history state
const currentConversationId = ref<string | null>(null);
const historyDropdownOpen = ref(false);
const conversationList = ref<ConversationItem[]>([]);
const historyDropdownContainer = ref<HTMLDivElement | null>(null);

// Computed current conversation title
const currentConversationTitle = computed(() => {
  if (!currentConversationId.value) return '';
  const current = conversationList.value.find(c => c.id === currentConversationId.value);
  return current?.title || '新对话';
});

// Filtered list (exclude current conversation)
const filteredConversationList = computed(() => {
  return conversationList.value.filter(c => c.id !== currentConversationId.value);
});

// Click outside to close dropdown
const handleClickOutside = (event: MouseEvent) => {
  if (historyDropdownContainer.value &&
      !historyDropdownContainer.value.contains(event.target as Node)) {
    historyDropdownOpen.value = false;
  }
};

// Format relative date for conversation list
const formatDate = (isoString: string): string => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    // Today - show time
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  } else if (diffDays === 1) {
    return '昨天';
  } else if (diffDays < 7) {
    return `${diffDays} 天前`;
  } else {
    // Show date
    return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
  }
};

// Toggle dropdown
const toggleHistoryDropdown = () => {
  if (!historyDropdownOpen.value) {
    // Load conversation list when opening
    loadConversationList();
  }
  historyDropdownOpen.value = !historyDropdownOpen.value;
};

// Load conversation list from backend
const loadConversationList = async () => {
  try {
    const response = await ConversationApi.listConversations();
    conversationList.value = response.conversations;
  } catch (err) {
    console.error('Failed to load conversation list:', err);
  }
};

// Switch to selected conversation
const switchConversation = async (conversationId: string) => {
  try {
    const response = await ConversationApi.getConversation(conversationId);
    // Convert to frontend ConversationMessage format
    const loadedMessages: ConversationMessage[] = response.messages.map(msg => ({
      id: `${Date.now()}-${Math.random()}`,
      role: (msg.role === 'model' ? 'model' : 'user') as 'user' | 'model',
      text: msg.content,
      timestamp: Date.now()
    }));

    // If we already have unsaved messages from user speaking while loading, keep them
    // Only replace if the loaded conversation actually has messages
    if (loadedMessages.length > 0 || conversationMessages.value.length === 0) {
      conversationMessages.value = loadedMessages;
    }
    // Otherwise: keep existing unsaved messages since they'll be saved later

    currentConversationId.value = conversationId;
    historyDropdownOpen.value = false;
  } catch (err) {
    console.error('Failed to switch conversation:', err);
    alert('加载对话失败，请重试');
  }
};

// Create new conversation
const createNewConversation = async () => {
  try {
    // Only clear if we don't already have messages (user might have started talking already)
    // If messages already exist (user started talking during initialization), keep them
    currentConversationId.value = null;
    if (conversationMessages.value.length === 0) {
      conversationMessages.value = [];
      currentModelMessage.value = '';
    }

    // Create empty conversation, title will be generated automatically
    // when user sends the first message on the backend
    const response = await ConversationApi.createConversation();
    currentConversationId.value = response.id;
    historyDropdownOpen.value = false;
    await loadConversationList();

    // If we already have user messages from early interaction before conversation was created,
    // save them to the backend now that we have a conversationId
    if (currentConversationId.value && conversationMessages.value.length > 0) {
      for (const msg of conversationMessages.value) {
        if (msg.role === 'user') {
          ConversationApi.addMessage(currentConversationId.value, 'user', msg.text)
            .catch(err => {
              console.error('Failed to save existing user message:', err);
            });
        } else if (msg.role === 'model') {
          ConversationApi.addMessage(currentConversationId.value, 'model', msg.text)
            .catch(err => {
              console.error('Failed to save existing model message:', err);
            });
        }
      }
      loadConversationList();
    }
  } catch (err) {
    console.error('Failed to create new conversation:', err);
    alert('创建新对话失败，请重试');
  }
};

// Delete a conversation
const deleteConversation = async (conversationId: string) => {
  if (!confirm('确定要删除这条对话记录吗？')) {
    return;
  }
  try {
    await ConversationApi.deleteConversation(conversationId);
    await loadConversationList();
    // If we deleted the current conversation, create a new one
    if (conversationId === currentConversationId.value) {
      await createNewConversation();
    }
  } catch (err) {
    console.error('Failed to delete conversation:', err);
    alert('删除失败，请重试');
  }
};

// Initialize conversation on mount
const initializeConversation = async () => {
  try {
    await loadConversationList();
    // If no current conversation selected, check if there's an active one
    const activeConv = conversationList.value.find(c => c.is_active);
    if (activeConv) {
      currentConversationId.value = activeConv.id;
      await switchConversation(activeConv.id);
    } else {
      // Create a new empty conversation
      await createNewConversation();
    }
  } catch (err) {
    console.error('Failed to initialize conversation:', err);
    // Fallback: create new conversation
    await createNewConversation();
  }
};

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
  // Initialize conversation from history
  initializeConversation();
  // Add click outside listener
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
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
      const userMessageId = Date.now().toString() + '-user';
      // Check if this is already in the list from ongoing updates
      const existingIndexFinal = conversationMessages.value.findIndex(
        m => m.id.startsWith('message-') || m.id === userMessageId
      );
      if (existingIndexFinal >= 0) {
        // Update existing bubble from streaming
        conversationMessages.value[existingIndexFinal].text = message.text;
      } else {
        // Add new bubble
        conversationMessages.value.push({
          id: userMessageId,
          role: 'user',
          text: message.text,
          timestamp: Date.now()
        });
      }
      currentModelMessage.value = '';
      // Save to backend if we have a conversation ID already
      if (currentConversationId.value) {
        ConversationApi.addMessage(currentConversationId.value, 'user', message.text)
          .then(() => {
            loadConversationList();
          })
          .catch(err => {
            console.error('Failed to save user message to conversation history:', err);
          });
      }
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

      // Save model message to backend after it's complete
      if (currentConversationId.value && conversationMessages.value.length > 0) {
        const lastMessage = conversationMessages.value[conversationMessages.value.length - 1];
        if (lastMessage.role === 'model' && lastMessage.text === currentModelMessage.value) {
          ConversationApi.addMessage(currentConversationId.value, 'model', lastMessage.text)
            .then(() => {
              loadConversationList();
            })
            .catch(err => {
              console.error('Failed to save model message:', err);
            });
        }
      }
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

async function sendUserInput() {
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

  // Save to backend if we have a current conversation
  if (currentConversationId.value) {
    try {
      await ConversationApi.addMessage(currentConversationId.value, 'user', text);
      // Update conversation list to reflect new message
      loadConversationList();
    } catch (err) {
      console.error('Failed to save message to conversation history:', err);
    }
  }

  userInputText.value = '';
}

function handleLogout() {
  authStore.logout();
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

/* Dropdown animations */
.dropdown-enter-active {
  transition: all 0.2s ease-out;
}
.dropdown-leave-active {
  transition: all 0.15s ease-in;
}
.dropdown-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}
.dropdown-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}
</style>
