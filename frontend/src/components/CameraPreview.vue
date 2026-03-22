<template>
  <div class="camera-preview full-screen">
    <video
      ref="videoRef"
      :srcObject="stream"
      autoplay
      playsinline
      muted
      class="video"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Props {
  stream: MediaStream | null;
}

defineProps<Props>();
const videoRef = ref<HTMLVideoElement | null>(null);
</script>

<style scoped>
.camera-preview {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  overflow: hidden;
}

.video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
