<template>
  <button
    class="camera-toggle"
    :class="{ enabled: enabled }"
    @click="$emit('toggle')"
  >
    <span class="icon">
      <svg v-if="enabled" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.35 4.8c-.2-.15-.44-.23-.7-.23H7v2h6l.35-.5zM19.75 7c-.69 0-1.25.56-1.25 1.25v4.21l2 2V8.25C20.5 7.56 19.94 7 19.25 7zM2.81 2.81L1.4 4.22 4.2 7H4v10c0 1.1.9 2 2 2h12.78l3 3 1.41-1.41L2.81 2.81zM7 9.81L10.19 13H7V9.81z"/>
      </svg>
    </span>
    <span class="label">{{ enabled ? '摄像头开启' : '摄像头关闭' }}</span>
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
.camera-toggle {
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

.camera-toggle:not(.enabled) {
  background: #6c757d;
  color: white;
}

.camera-toggle.enabled {
  background: #007bff;
  color: white;
}

.icon {
  font-size: 1.2rem;
}
</style>
