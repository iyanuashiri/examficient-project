<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      exams: [],
      loading: true,
      error: '',
    }
  },
  async created() {
    try {
      this.exams = await apiFetch('/exams/mine/')
    } catch (e) {
      this.error = e.message
      if (e.status === 401) this.$router.push('/login')
    } finally {
      this.loading = false
    }
  },
}
</script>

<template>
  <div>
    <h2 class="font-display text-2xl font-bold tracking-tight">Challenges</h2>
    <p class="mt-1 text-sm text-slate-500">Explain concepts in your own words. The AI grades depth — XP scales, mastery untouched.</p>
    <p v-if="loading" class="mt-4 text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <div v-if="!loading" class="mt-4 grid gap-3 sm:grid-cols-2">
      <router-link
        v-for="e in exams"
        :key="e.id"
        :to="`/challenges/${e.id}`"
        class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-400"
      >
        <p class="font-display text-lg font-bold">{{ e.name }}</p>
        <p class="mt-1 text-xs font-semibold text-slate-500">Open challenge board →</p>
      </router-link>
      <p v-if="!exams.length" class="text-sm text-slate-500">No exams yet — enroll in one first.</p>
    </div>
  </div>
</template>
