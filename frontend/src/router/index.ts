import { createRouter, createWebHistory } from 'vue-router';
import LoginPage from '@/components/LoginPage.vue';
import VideoCallPage from '@/components/VideoCallPage.vue';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginPage
    },
    {
      path: '/call',
      name: 'call',
      component: VideoCallPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      redirect: () => {
        const auth = useAuthStore();
        return auth.isAuthenticated || auth.isGuest ? '/call' : '/login';
      }
    }
  ]
});

router.beforeEach((to, from, next) => {
  const auth = useAuthStore();
  auth.loadFromStorage();

  if (to.meta.requiresAuth && !auth.isAuthenticated && !auth.isGuest) {
    next('/login');
  } else if (to.path === '/login' && (auth.isAuthenticated || auth.isGuest)) {
    next('/call');
  } else {
    next();
  }
});

export default router;
