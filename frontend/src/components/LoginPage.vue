<template>
  <div class="min-h-screen w-full bg-black flex items-center justify-center p-4 relative overflow-hidden">
    <!-- 背景光效 -->
    <div class="absolute inset-0">
      <div
        class="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[120px] animate-bg-pulse-1"
      ></div>
      <div
        class="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[120px] animate-bg-pulse-2"
      ></div>
    </div>

    <div
      class="w-full max-w-md relative z-10 animate-fade-in-up"
    >
      <!-- Logo和标题 -->
      <div class="text-center mb-16">
        <div
          class="inline-flex items-center justify-center mb-8 animate-scale-in"
        >
          <Sparkles class="w-12 h-12 text-indigo-400" />
        </div>
        <h1
          class="text-5xl font-bold text-white mb-4 tracking-tight animate-title-in"
        >
          SeeWorld AI
        </h1>
        <p
          class="text-gray-400 text-lg animate-subtitle-in"
        >
          实时视觉对话智能体
        </p>
      </div>

      <!-- 登录按钮 -->
      <div class="space-y-3">
        <button
          @click="loginWithHuawei"
          class="w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white py-5 rounded-2xl font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:border-red-500/50 hover:bg-red-500/15 hover:scale-[1.02] active:scale-[0.98] animate-btn-1"
        >
          <Smartphone class="w-5 h-5" />
          华为账号
        </button>

        <button
          @click="loginWithWechat"
          class="w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white py-5 rounded-2xl font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:border-green-500/50 hover:bg-green-500/15 hover:scale-[1.02] active:scale-[0.98] animate-btn-2"
        >
          <MessageSquare class="w-5 h-5" />
          微信账号
        </button>

        <button
          @click="enterAsGuest"
          class="w-full bg-white/5 backdrop-blur-sm border border-white/10 text-white py-5 rounded-2xl font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:border-indigo-500/50 hover:bg-indigo-500/15 hover:scale-[1.02] active:scale-[0.98] animate-btn-3"
        >
          <Eye class="w-5 h-5" />
          访客体验
        </button>
      </div>

      <!-- 底部提示 -->
      <p
        class="text-center text-sm text-gray-600 mt-12 animate-footer-in"
      >
        登录即表示同意服务条款与隐私政策
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { UserInfo } from '@seeworldweb/shared/src/types';
import { Sparkles, Smartphone, MessageSquare, Eye } from 'lucide-vue-next';

const router = useRouter();
const authStore = useAuthStore();
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

onMounted(() => {
  // Check if we have token in URL after OAuth callback
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  const userStr = urlParams.get('user');

  if (token && userStr) {
    try {
      const user: UserInfo = JSON.parse(decodeURIComponent(userStr));
      authStore.setAuth(token, user);
      router.push('/call');
    } catch (e) {
      console.error('Failed to parse user from URL', e);
    }
  }
});

function loginWithHuawei() {
  window.location.href = `${apiUrl}/auth/huawei`;
}

function loginWithWechat() {
  window.location.href = `${apiUrl}/auth/wechat`;
}

function enterAsGuest() {
  authStore.guestLogin();
}
</script>

<style>
@keyframes bgPulse1 {
  0%, 100% {
    transform: scale(1);
    opacity: 0.3;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.5;
  }
}

@keyframes bgPulse2 {
  0%, 100% {
    transform: scale(1.2);
    opacity: 0.5;
  }
  50% {
    transform: scale(1);
    opacity: 0.3;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translate3d(0, 20px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-bg-pulse-1 {
  animation: bgPulse1 8s infinite ease-in-out;
}

.animate-bg-pulse-2 {
  animation: bgPulse2 8s infinite ease-in-out;
}

.animate-fade-in-up {
  animation: fadeInUp 0.8s ease-out forwards;
}

.animate-scale-in {
  animation: scaleIn 0.5s ease forwards;
}

.animate-title-in {
  animation: fadeInUp 0.8s ease-out 0.3s forwards;
  opacity: 0;
}

.animate-subtitle-in {
  animation: fadeInUp 0.8s ease-out 0.4s forwards;
  opacity: 0;
}

.animate-btn-1 {
  animation: fadeInUp 0.8s ease-out 0.5s forwards;
  opacity: 0;
}

.animate-btn-2 {
  animation: fadeInUp 0.8s ease-out 0.6s forwards;
  opacity: 0;
}

.animate-btn-3 {
  animation: fadeInUp 0.8s ease-out 0.7s forwards;
  opacity: 0;
}

.animate-footer-in {
  animation: fadeInUp 0.8s ease-out 0.8s forwards;
  opacity: 0;
}
</style>
