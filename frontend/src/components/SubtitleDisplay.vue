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
  </div>
</template>

<script setup lang="ts">
import { ConversationMessage } from '@seeworldweb/shared/src/types';
import { SUBTITLE_OPACITY_WITH_CAMERA } from '@seeworldweb/shared/src/constants';

interface Props {
  messages: ConversationMessage[];
  cameraEnabled: boolean;
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
</style>
