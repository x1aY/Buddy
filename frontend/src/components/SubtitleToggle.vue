<template>
  <BaseToggleButton
    :enabled="enabled"
    label-on="字幕开启"
    label-off="字幕关闭"
    active-class="bg-amber-500 text-white"
    :icon-on="Subtitles"
    :icon-off="Subtitles"
    @toggle="$emit('toggle')"
  />
</template>

<script setup lang="ts">
import { Subtitles } from 'lucide-vue-next';
import BaseToggleButton from './BaseToggleButton.vue';

interface Props {
  enabled: boolean;
}

const props = defineProps<Props>();
defineEmits<{
  toggle: [];
}>();
</script>
