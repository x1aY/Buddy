<template>
  <div
    class="w-full h-full p-4 flex flex-col gap-3 overflow-y-auto"
    :class="cameraEnabled ? 'bg-black/20 opacity-85 backdrop-blur-sm rounded-xl m-4' : ''"
  >
    <div
      v-for="message in messages"
      :key="message.id"
      :class="[
        'max-w-md px-6 py-4 rounded-2xl shadow-lg',
        message.role === 'user'
          ? cameraEnabled
            ? 'self-end bg-indigo-600/70 text-white backdrop-blur-md'
            : 'self-end bg-indigo-600 text-white'
          : cameraEnabled
            ? 'self-start bg-gray-800/70 text-white backdrop-blur-md'
            : 'self-start bg-gray-700 text-white'
      ]"
    >
      <p class="text-base leading-relaxed">{{ message.text }}</p>
    </div>
    <!-- Real-time partial transcript (recognized while speaking) -->
    <div v-if="partialText" class="flex justify-end mt-2">
      <div class="max-w-md px-4 py-2 rounded-xl bg-indigo-600/40 text-white/70 italic">
        <p class="text-sm">{{ partialText }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ConversationMessage } from '@seeworldweb/shared/src/types';

interface Props {
  messages: ConversationMessage[];
  cameraEnabled: boolean;
  partialText: string;
}

defineProps<Props>();
</script>
