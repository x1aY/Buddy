<template>
  <button
    class="subtitle-toggle"
    :class="{ enabled: enabled }"
    @click="$emit('toggle')"
  >
    <span class="icon">{{ enabled ? '📖' : '📝' }}</span>
    <span class="label">{{ enabled ? '字幕开启' : '字幕关闭' }}</span>
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
.subtitle-toggle {
  padding: 0.75rem 1.25rem;
  border-radius: 50px;
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.subtitle-toggle:not(.enabled) {
  background: #6c757d;
  color: white;
}

.subtitle-toggle.enabled {
  background: #ffc107;
  color: #333;
}

.icon {
  font-size: 1.1rem;
}
</style>
