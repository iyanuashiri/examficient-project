<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      attempts: [],
      error: '',
      loading: true,
      wrongOnly: false,
    }
  },
  computed: {
    id() {
      return this.$route.params.id
    },
  },
  async created() {
    await this.load()
  },
  methods: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.attempts = await apiFetch(
          `/practice/history/?exam_id=${this.id}&wrong_only=${this.wrongOnly}&limit=100`,
        )
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
  },
  watch: {
    wrongOnly() {
      this.load()
    },
  },
}
</script>

<template>
  <div>
    <router-link :to="`/exams/${this.id}`" class="text-sm text-slate-500 hover:text-slate-900">← back</router-link>
    <div class="mb-4 mt-2 flex items-center justify-between">
      <h2 class="font-display text-2xl font-bold tracking-tight">Review history</h2>
      <label class="flex items-center gap-2 text-sm"><input v-model="wrongOnly" type="checkbox" /> wrong only</label>
    </div>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <p v-if="!attempts.length && !loading" class="text-sm text-slate-500">Nothing here yet — go practice.</p>
    <div v-for="a in attempts" :key="a.attempt_id" class="mb-2 rounded-3xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
      <p class="font-medium">{{ a.stem }}</p>
      <p class="mt-1" :class="a.correct ? 'text-emerald-700' : 'text-red-600'">
        {{ a.correct ? '✓ Correct' : '✗ Wrong' }}
        <span class="text-slate-400">· {{ new Date(a.answered_at).toLocaleString() }}</span>
      </p>
    </div>
  </div>
</template>
