<template>
  <BaseToggleButton
    :enabled="enabled"
    label-on="摄像头开启"
    label-off="摄像头关闭"
    active-class="bg-blue-500 text-white"
    :icon-on="Video"
    :icon-off="VideoOff"
    @toggle="$emit('toggle')"
  />
</template>

<script setup lang="ts">
import { Video, VideoOff } from 'lucide-vue-next';
import BaseToggleButton from './BaseToggleButton.vue';

interface Props {
  enabled: boolean;
}

const props = defineProps<Props>();
defineEmits<{
  toggle: [];
}>();
</script>
