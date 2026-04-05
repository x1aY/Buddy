<template>
  <BaseToggleButton
    :enabled="enabled"
    label-on="声音开启"
    label-off="声音关闭"
    active-class="bg-green-500 text-white"
    :icon-on="Mic"
    :icon-off="MicOff"
    @toggle="$emit('toggle')"
  />
</template>

<script setup lang="ts">
import { Mic, MicOff } from 'lucide-vue-next';
import BaseToggleButton from './BaseToggleButton.vue';

interface Props {
  enabled: boolean;
}

const props = defineProps<Props>();
defineEmits<{
  toggle: [];
}>();
</script>
