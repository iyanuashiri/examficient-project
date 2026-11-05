<script>
import { getToken, clearToken } from './api/client.js'

export default {
  data() {
    return { authed: !!getToken(), sidebarOpen: false }
  },
  computed: {
    isLanding() {
      return this.$route.path === '/'
    },
  },
  watch: {
    $route() {
      this.authed = !!getToken()
      this.sidebarOpen = false
    },
  },
  methods: {
    logout() {
      clearToken()
      this.authed = false
      this.sidebarOpen = false
      this.$router.push('/login')
    },
  },
}
</script>

<template>
  <div
    :class="isLanding ? 'min-h-screen bg-white font-sans text-slate-900' : 'min-h-screen bg-slate-50 font-sans text-slate-900'"
  >
    <!-- Landing / logged-out nav -->
    <nav
      v-if="isLanding || !authed"
      :class="isLanding ? 'border-b border-slate-200/70 bg-white/80 backdrop-blur' : 'border-b border-slate-200 bg-white'"
      class="sticky top-0 z-50"
    >
      <div
        :class="isLanding ? 'mx-auto flex max-w-6xl items-center gap-4 px-4 py-3' : 'mx-auto flex max-w-3xl items-center gap-4 px-4 py-3'"
      >
        <router-link to="/" class="font-display text-lg font-bold text-slate-900">Examficient<span class="text-emerald-500">.</span></router-link>
        <span class="flex-1"></span>
        <template v-if="authed">
          <router-link to="/home" class="text-sm text-slate-600 hover:text-slate-900">Dashboard</router-link>
          <router-link to="/exams" class="text-sm text-slate-600 hover:text-slate-900">Exams</router-link>
          <button @click="logout" class="text-sm text-slate-600 hover:text-slate-900">Logout</button>
        </template>
        <template v-else>
          <router-link to="/login" class="text-sm text-slate-600 hover:text-slate-900">Login</router-link>
          <router-link to="/register" class="rounded-full bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700">Get started</router-link>
        </template>
      </div>
    </nav>

    <!-- Logged-in sidebar shell -->
    <div v-else class="min-h-screen md:flex">
      <!-- Mobile top bar -->
      <div class="sticky top-0 z-40 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:hidden">
        <button @click="sidebarOpen = !sidebarOpen" aria-label="Menu" class="rounded-lg p-1.5 hover:bg-slate-100">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="6" x2="20" y2="6" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="18" x2="20" y2="18" /></svg>
        </button>
        <router-link to="/" class="font-display text-lg font-bold text-slate-900">Examficient<span class="text-emerald-500">.</span></router-link>
      </div>

      <!-- Backdrop -->
      <div v-if="sidebarOpen" @click="sidebarOpen = false" class="fixed inset-0 z-40 bg-slate-900/40 md:hidden"></div>

      <!-- Sidebar -->
      <aside
        class="fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0"
        :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
      >
        <router-link to="/" class="px-5 pb-2 pt-5 font-display text-lg font-bold text-slate-900">Examficient<span class="text-emerald-500">.</span></router-link>
        <nav class="flex-1 space-y-1 px-3 py-4">
          <router-link
            to="/home"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Dashboard</router-link>
          <router-link
            to="/exams"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Exams</router-link>
          <router-link
            to="/rooms"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Rooms</router-link>
          <router-link
            to="/challenges"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Challenges</router-link>
          <router-link
            to="/analytics"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Analytics</router-link>
          <router-link
            to="/profile"
            active-class="bg-slate-900 text-white"
            class="block rounded-2xl px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >Profile</router-link>
        </nav>
        <div class="border-t border-slate-200 p-3">
          <button @click="logout" class="block w-full rounded-2xl px-4 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-slate-100">Logout</button>
        </div>
      </aside>

      <!-- Content -->
      <main class="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        <router-view />
      </main>
    </div>

    <main v-if="isLanding || !authed" :class="isLanding ? '' : 'mx-auto max-w-3xl px-4 py-6'">
      <router-view />
    </main>
  </div>
</template>
