<template>
  <div class="login-page flex-center full-screen">
    <div class="login-card">
      <h1 class="title">SeeWorld AI</h1>
      <p class="subtitle">与AI进行实时音视频对话</p>

      <div class="login-buttons">
        <button class="login-btn huawei" @click="loginWithHuawei">
          <span class="icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z"/>
            </svg>
          </span>
          华为账号登录
        </button>
        <button class="login-btn wechat" @click="loginWithWechat">
          <span class="icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2z"/>
            </svg>
          </span>
          微信账号登录
        </button>
        <div class="divider"></div>
        <button class="login-btn guest" @click="enterAsGuest">
          <span class="icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
            </svg>
          </span>
          游客体验
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { UserInfo } from '@seeworldweb/shared/src/types';

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

<style scoped>
.login-page {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: white;
  padding: 3rem 2rem;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  text-align: center;
  min-width: 320px;
}

.title {
  font-size: 2rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
}

.login-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.login-btn {
  padding: 1rem 2rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.login-btn .icon {
  font-size: 1.2rem;
}

.huawei {
  background-color: #c00000;
  color: white;
}

.wechat {
  background-color: #07c160;
  color: white;
}

.guest {
  background-color: #f0f0f0;
  color: #666;
  border: 1px solid #ddd;
}

.divider {
  height: 1px;
  background-color: #eee;
  margin: 0.5rem 0;
}
</style>
