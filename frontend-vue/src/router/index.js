import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/api/client.js'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ExamsView from '@/views/ExamsView.vue'
import ExamDetailView from '@/views/ExamDetailView.vue'
import ManageView from '@/views/ManageView.vue'
import HistoryView from '@/views/HistoryView.vue'
import AnalyticsView from '@/views/AnalyticsView.vue'
import PracticeView from '@/views/PracticeView.vue'
import RoomView from '@/views/RoomView.vue'
import RoomBoardView from '@/views/RoomBoardView.vue'
import RoomsView from '@/views/RoomsView.vue'
import ChallengesView from '@/views/ChallengesView.vue'
import ChallengeView from '@/views/ChallengeView.vue'
import ProfileView from '@/views/ProfileView.vue'
import LandingView from '@/views/LandingView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', component: LandingView },
    { path: '/login', component: LoginView },
    { path: '/register', component: RegisterView },
    { path: '/home', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/exams', component: ExamsView, meta: { requiresAuth: true } },
    { path: '/exams/:id', component: ExamDetailView, meta: { requiresAuth: true } },
    { path: '/exams/:id/manage', component: ManageView, meta: { requiresAuth: true } },
    { path: '/exams/:id/history', component: HistoryView, meta: { requiresAuth: true } },
    { path: '/analytics', component: AnalyticsView, meta: { requiresAuth: true } },
    { path: '/practice/:id', component: PracticeView, meta: { requiresAuth: true } },
    { path: '/rooms', component: RoomsView, meta: { requiresAuth: true } },
    { path: '/rooms/:id', component: RoomView, meta: { requiresAuth: true } },
    { path: '/rooms/:id/board', component: RoomBoardView, meta: { requiresAuth: true } },
    { path: '/challenges', component: ChallengesView, meta: { requiresAuth: true } },
    { path: '/challenges/:id', component: ChallengeView, meta: { requiresAuth: true } },
    { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !getToken()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
