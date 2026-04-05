<template>
  <div class="absolute inset-0 z-0 overflow-hidden">
    <video
      ref="videoRef"
      autoplay
      playsinline
      muted
      class="w-full h-full object-cover"
    />
    <div class="absolute inset-0 bg-black/20"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

interface Props {
  stream: MediaStream | null;
}

const props = defineProps<Props>();
const videoRef = ref<HTMLVideoElement | null>(null);

// Update srcObject when stream changes
watch(() => props.stream, (newStream) => {
  if (videoRef.value && newStream) {
    videoRef.value.srcObject = newStream;
  }
}, { immediate: true });
</script>
