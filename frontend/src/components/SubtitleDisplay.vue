<template>
  <div class="subtitle-container" :class="{ 'camera-on': cameraEnabled }">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-bubble"
      :class="[message.role === 'user' ? 'user' : 'model']"
    >
      {{ message.text }}
    </div>
    <!-- Real-time partial transcript (recognized while speaking) -->
    <div v-if="partialText" class="partial-transcript">
      <span class="recording-indicator"></span>
      {{ partialText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ConversationMessage } from '@seeworldweb/shared/src/types';
import { SUBTITLE_OPACITY_WITH_CAMERA } from '@seeworldweb/shared/src/constants';

interface Props {
  messages: ConversationMessage[];
  cameraEnabled: boolean;
  partialText: string;
}

defineProps<Props>();
</script>

<style scoped>
.subtitle-container {
  width: 100%;
  height: 100%;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  margin: 1rem;
  transition: opacity 0.3s ease;
}

.subtitle-container.camera-on {
  background: rgba(0, 0, 0, 0.2);
  opacity: 0.3;
}

.message-bubble {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 16px;
  font-size: 1rem;
  line-height: 1.4;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-bubble.user {
  align-self: flex-end;
  background: #007bff;
  color: white;
}

.message-bubble.model {
  align-self: flex-start;
  background: white;
  color: #333;
}

/* Partial transcript (real-time recognition) */
.partial-transcript {
  align-self: center;
  max-width: 90%;
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
  color: #666;
  font-size: 0.9rem;
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Animated recording indicator */
.recording-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc3545;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
</style>
