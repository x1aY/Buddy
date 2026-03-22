import { defineStore } from 'pinia';
import { UserInfo } from '@seeworldweb/shared/src/types';
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter();
  const token = ref<string | null>(null);
  const user = ref<UserInfo | null>(null);
  const isGuestMode = ref<boolean>(false);

  const isAuthenticated = computed(() => !!token.value && !!user.value);
  const isGuest = computed(() => isGuestMode.value);

  function setAuth(newToken: string, newUser: UserInfo) {
    token.value = newToken;
    user.value = newUser;
    isGuestMode.value = false;
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));
    localStorage.removeItem('isGuest');
  }

  function guestLogin() {
    token.value = null;
    user.value = null;
    isGuestMode.value = true;
    localStorage.setItem('isGuest', 'true');
    router.push('/call');
  }

  function logout() {
    token.value = null;
    user.value = null;
    isGuestMode.value = false;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('isGuest');
    router.push('/login');
  }

  function loadFromStorage() {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    const savedIsGuest = localStorage.getItem('isGuest');
    if (savedToken && savedUser) {
      token.value = savedToken;
      try {
        user.value = JSON.parse(savedUser);
      } catch {
        logout();
      }
    }
    if (savedIsGuest === 'true') {
      isGuestMode.value = true;
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    isGuest,
    setAuth,
    guestLogin,
    logout,
    loadFromStorage
  };
});
