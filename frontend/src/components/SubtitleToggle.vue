<template>
  <button
    class="subtitle-toggle"
    :class="{ enabled: enabled }"
    @click="$emit('toggle')"
  >
    <span class="icon">
      <svg v-if="enabled" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 12h4v2H4v-2zm10 6H4v-2h10v2zm6 0h-4v-2h4v2zm0-4H10v-2h10v2z"/>
      </svg>
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 16v-2h10v2H4zm0-4V8h16v4H4z"/>
      </svg>
    </span>
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
