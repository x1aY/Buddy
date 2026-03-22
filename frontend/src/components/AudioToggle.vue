<template>
  <button
    class="audio-toggle"
    :class="{ enabled: enabled }"
    @click="$emit('toggle')"
  >
    <span class="icon">{{ enabled ? '🔊' : '🔇' }}</span>
    <span class="label">{{ enabled ? '声音开启' : '声音关闭' }}</span>
  </button>
</template>

<script setup lang="ts">
interface Props {
  enabled: boolean;
}

const props = defineProps<Props>();
defineEmits<{
  toggle: [];
}>();
</script>

<style scoped>
.audio-toggle {
  padding: 1rem 1.5rem;
  border-radius: 50px;
  font-size: 1rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.audio-toggle:not(.enabled) {
  background: #6c757d;
  color: white;
}

.audio-toggle.enabled {
  background: #28a745;
  color: white;
}

.icon {
  font-size: 1.2rem;
}
</style>
