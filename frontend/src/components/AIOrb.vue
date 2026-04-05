<script setup lang="ts">
type AIState = "listening" | "thinking" | "speaking";

interface Props {
  state: AIState;
}

defineProps<Props>();
</script>

<template>
  <div class="inline-block relative">
    <svg width="280" height="280" viewBox="0 0 280 280" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- 背景光晕 -->
      <circle
        cx="140" cy="140" r="120"
        fill="url(#glowGradient)"
        opacity="0.3"
        :class="[
          'transition-all duration-150 ease-in-out',
          state === 'speaking' ? 'animate-orb-glow' : ''
        ]"
      />

      <!-- 外层波纹 - 说话状态 -->
      <g v-if="state === 'speaking'">
        <circle
          cx="140" cy="140" r="90"
          stroke="url(#ringGradient)"
          stroke-width="2"
          fill="none"
          class="animate-orb-ripple-1"
        />
        <circle
          cx="140" cy="140" r="90"
          stroke="url(#ringGradient)"
          stroke-width="2"
          fill="none"
          class="animate-orb-ripple-2"
        />
        <circle
          cx="140" cy="140" r="90"
          stroke="url(#ringGradient)"
          stroke-width="2"
          fill="none"
          class="animate-orb-ripple-3"
        />
      </g>

      <!-- 主球体 -->
      <circle
        cx="140" cy="140" r="70"
        fill="url(#orbGradient)"
        :class="[
          'transition-all',
          state === 'listening' ? 'animate-orb-listener' : '',
          state === 'speaking' ? 'animate-orb-speaking' : ''
        ]"
      />

      <!-- 球体高光 -->
      <ellipse cx="120" cy="120" rx="25" ry="30" fill="white" opacity="0.3" />

      <!-- 思考状态 - 旋转环 -->
      <g v-if="state === 'thinking'" class="animate-orb-thinking">
        <!-- 外环 -->
        <circle
          cx="140" cy="140" r="85"
          stroke="url(#thinkingGradient)"
          stroke-width="3"
          fill="none"
          stroke-dasharray="20 10"
          opacity="0.6"
        />

        <!-- 中环 -->
        <circle
          cx="140" cy="140" r="95"
          stroke="url(#thinkingGradient)"
          stroke-width="2"
          fill="none"
          stroke-dasharray="15 15"
          opacity="0.4"
          class="animate-orb-thinking-reverse"
        />

        <!-- 装饰点 -->
        <circle cx="225" cy="140" r="4" fill="#a78bfa" opacity="0.8" />
        <circle cx="140" cy="55" r="3" fill="#c4b5fd" opacity="0.6" />
        <circle cx="55" cy="140" r="3.5" fill="#8b5cf6" opacity="0.7" />
      </g>

      <!-- 核心粒子效果 -->
      <g :opacity="state === 'thinking' ? '0.8' : '0.5'">
        <!-- 粒子1 -->
        <circle
          cx="140" cy="140" r="3"
          fill="#a78bfa"
          class="animate-orb-particle-1"
        />
        <!-- 粒子2 -->
        <circle
          cx="140" cy="140" r="2.5"
          fill="#c4b5fd"
          class="animate-orb-particle-2"
        />
        <!-- 粒子3 -->
        <circle
          cx="140" cy="140" r="2"
          fill="#8b5cf6"
          class="animate-orb-particle-3"
        />
      </g>

      <!-- 内部光芒 -->
      <circle
        cx="140" cy="140" r="35"
        fill="white"
        opacity="0.4"
        class="animate-orb-inner-glow"
      />

      <!-- 渐变定义 -->
      <defs>
        <radialGradient id="orbGradient">
          <stop offset="0%" stop-color="#c4b5fd" />
          <stop offset="50%" stop-color="#a78bfa" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </radialGradient>

        <radialGradient id="glowGradient">
          <stop offset="0%" stop-color="#a78bfa" />
          <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0" />
        </radialGradient>

        <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#c4b5fd" />
          <stop offset="100%" stop-color="#8b5cf6" />
        </linearGradient>

        <linearGradient id="thinkingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#a78bfa" />
          <stop offset="50%" stop-color="#8b5cf6" />
          <stop offset="100%" stop-color="#7c3aed" />
        </linearGradient>
      </defs>
    </svg>

    <!-- 状态文字提示 -->
    <div class="absolute -bottom-12 left-1/2 transform -translate-x-1/2 text-center">
      <p class="text-gray-400 text-sm font-medium">
        <template v-if="state === 'listening'">正在听...</template>
        <template v-else-if="state === 'thinking'">思考中...</template>
        <template v-else-if="state === 'speaking'">正在回复</template>
      </p>
    </div>
  </div>
</template>

<style>
@keyframes orb-glow {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.6;
  }
}

@keyframes orb-ripple-1 {
  0% {
    transform: scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

@keyframes orb-ripple-2 {
  0% {
    transform: scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

@keyframes orb-ripple-3 {
  0% {
    transform: scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

@keyframes orb-listener {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(0.85); }
}

@keyframes orb-speaking {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

@keyframes orb-thinking {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes orb-thinking-reverse {
  from { transform: rotate(0deg); }
  to { transform: rotate(-360deg); }
}

@keyframes orb-particle-1 {
  0%, 100% {
    transform: translate(0, 0);
    opacity: 0.8;
  }
  50% {
    transform: translate(15px, -15px);
    opacity: 0.3;
  }
}

@keyframes orb-particle-2 {
  0%, 100% {
    transform: translate(0, 0);
    opacity: 0.8;
  }
  50% {
    transform: translate(-12px, 12px);
    opacity: 0.3;
  }
}

@keyframes orb-particle-3 {
  0%, 100% {
    transform: translate(0, 0);
    opacity: 0.8;
  }
  50% {
    transform: translate(18px, 10px);
    opacity: 0.3;
  }
}

@keyframes orb-inner-glow {
  0%, 100% {
    transform: scale(1);
    opacity: 0.4;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.2;
  }
}

.animate-orb-glow {
  animation: orb-glow 1.5s infinite ease-in-out;
}

.animate-orb-ripple-1 {
  animation: orb-ripple-1 2s infinite ease-out;
}

.animate-orb-ripple-2 {
  animation: orb-ripple-2 2s infinite ease-out 0.6s;
}

.animate-orb-ripple-3 {
  animation: orb-ripple-3 2s infinite ease-out 1.2s;
}

.animate-orb-listener {
  animation: orb-listener 2s infinite ease-in-out;
}

.animate-orb-speaking {
  animation: orb-speaking 1.5s infinite ease-in-out;
}

.animate-orb-thinking {
  animation: orb-thinking 3s infinite linear;
  transform-origin: 140px 140px;
}

.animate-orb-thinking-reverse {
  animation: orb-thinking-reverse 4s infinite linear;
  transform-origin: 140px 140px;
}

.animate-orb-particle-1 {
  animation: orb-particle-1 2.5s infinite ease-in-out;
}

.animate-orb-particle-2 {
  animation: orb-particle-2 2.5s infinite ease-in-out 0.8s;
}

.animate-orb-particle-3 {
  animation: orb-particle-3 2.5s infinite ease-in-out 1.6s;
}

.animate-orb-inner-glow {
  animation: orb-inner-glow 2s infinite ease-in-out;
}
</style>
