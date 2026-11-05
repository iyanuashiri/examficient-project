<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      exam: null,
      readiness: null,
      progress: null,
      topics: [],
      enrolled: false,
      isOwner: false,
      error: '',
      loading: true,
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
  watch: {
    '$route.params.id'() {
      this.load()
    },
  },
  methods: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        this.exam = await apiFetch(`/exams/${this.id}/`)
        const [me, mine] = await Promise.all([
          apiFetch('/users/me/'),
          apiFetch('/exams/mine/'),
        ])
        this.isOwner = this.exam.user_id != null && me.id === this.exam.user_id
        this.enrolled = mine.some((e) => e.id === Number(this.id))
        if (this.enrolled || this.isOwner) {
          const [readiness, stats] = await Promise.all([
            apiFetch(`/practice/readiness/?exam_id=${this.id}`),
            apiFetch(`/practice/stats/?exam_id=${this.id}`),
          ])
          this.readiness = readiness
          this.progress = stats
        } else {
          this.readiness = null
          this.progress = null
        }
        const syllabi = await apiFetch(`/exams/${this.id}/syllabi/`)
        const current = syllabi.find((s) => s.is_current) || syllabi[0]
        this.topics = current ? await apiFetch(`/syllabi/${current.id}/topics/`) : []
      } catch (e) {
        this.error = e.message
        if (e.status === 401) this.$router.push('/login')
      } finally {
        this.loading = false
      }
    },
    async joinExam() {
      this.error = ''
      try {
        await apiFetch(`/exams/${this.id}/enroll/`, { method: 'POST' })
        this.enrolled = true
      } catch (e) {
        this.error = e.message
      }
    },
    async leaveExam() {
      this.error = ''
      try {
        await apiFetch(`/exams/${this.id}/enroll/`, { method: 'DELETE' })
        this.enrolled = false
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>

<template>
  <div>
    <router-link to="/exams" class="text-sm text-slate-500 hover:text-slate-900">← Exams</router-link>
    <p v-if="loading" class="mt-2 text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <template v-if="exam">
      <h2 class="mb-1 mt-2 font-display text-3xl font-bold tracking-tight">{{ exam.name }}</h2>
      <p class="text-sm text-slate-500">{{ exam.code }} · {{ exam.issuing_body || '' }} {{ exam.country || '' }}</p>
      <p v-if="exam.description" class="mt-2 text-slate-600">{{ exam.description }}</p>

      <div v-if="readiness && readiness.topics_attempted > 0" class="mt-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex items-baseline justify-between">
          <p class="text-sm font-semibold tracking-widest text-slate-400">YOUR READINESS</p>
          <p class="font-display text-3xl font-bold">{{ readiness.predicted_score_pct }}<span class="text-base text-slate-400">%</span></p>
        </div>
        <p v-if="readiness.pass_mark != null" class="mt-1 text-sm" :class="readiness.on_track ? 'text-emerald-700' : 'text-amber-700'">
          {{ readiness.on_track ? 'Clear to pass' : `${readiness.points_to_pass} points to pass mark ${readiness.pass_mark}%` }}
        </p>
        <ul v-if="readiness.weak_topics.length" class="mt-2 list-disc pl-5 text-sm text-slate-600">
          <li v-for="t in readiness.weak_topics" :key="t.topic_id">{{ t.name }} — {{ Math.round(t.mastery_p * 100) }}%</li>
        </ul>
      </div>

      <div v-if="progress && progress.questions_answered > 0" class="mt-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold tracking-widest text-slate-400">YOUR PRACTICE SO FAR</p>
        <div class="mt-2 grid grid-cols-3 gap-2 text-center sm:grid-cols-6">
          <div><p class="font-display text-xl font-bold">{{ progress.questions_answered }}</p><p class="text-xs text-slate-500">answered</p></div>
          <div><p class="font-display text-xl font-bold text-emerald-700">{{ progress.questions_correct }}</p><p class="text-xs text-slate-500">correct</p></div>
          <div><p class="font-display text-xl font-bold text-red-600">{{ progress.questions_wrong }}</p><p class="text-xs text-slate-500">wrong</p></div>
          <div><p class="font-display text-xl font-bold">{{ progress.accuracy_pct }}<span class="text-sm">%</span></p><p class="text-xs text-slate-500">accuracy</p></div>
          <div><p class="font-display text-xl font-bold">{{ progress.topics_practiced }}</p><p class="text-xs text-slate-500">topics tried</p></div>
          <div><p class="font-display text-xl font-bold">{{ progress.streak_days }}</p><p class="text-xs text-slate-500">day streak</p></div>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <router-link v-if="enrolled || isOwner" :to="`/practice/${exam.id}`" class="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Start practice →</router-link>
        <button v-else @click="joinExam" class="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Enroll in this exam</button>
        <button v-if="enrolled && !isOwner" @click="leaveExam" class="rounded-full border border-slate-300 px-6 py-2.5 text-sm font-semibold hover:bg-slate-50">Leave</button>
        <router-link :to="`/exams/${exam.id}/history`" class="rounded-full border border-slate-300 px-6 py-2.5 text-sm font-semibold hover:bg-slate-50">Review history</router-link>
      </div>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Topics</h3>
      <ul class="list-disc pl-5 text-sm text-slate-600">
        <li v-for="t in topics" :key="t.id">{{ t.code ? `${t.code} — ` : '' }}{{ t.name }}</li>
      </ul>
      <p v-if="!topics.length && !loading" class="text-sm text-slate-500">No syllabus published yet.</p>
    </template>
  </div>
</template>
