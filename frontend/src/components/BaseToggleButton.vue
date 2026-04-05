<template>
  <button
    :class="['btn-toggle-base', enabled ? activeClass : 'btn-toggle-inactive']"
    @click="$emit('toggle')"
  >
    <component :is="enabled ? props.iconOn : props.iconOff" class="w-5 h-5" />
    <span>{{ enabled ? props.labelOn : props.labelOff }}</span>
  </button>
</template>

<script setup lang="ts">
import type { Component } from 'vue';

interface Props {
  enabled: boolean;
  labelOn: string;
  labelOff: string;
  activeClass: string;
  iconOn: Component;
  iconOff: Component;
}

const props = defineProps<Props>();
defineEmits<{
  toggle: [];
}>();
</script>
