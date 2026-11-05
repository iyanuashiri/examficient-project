<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      exams: [],
      examId: null,
      data: null,
      error: '',
      loading: true,
    }
  },
  async created() {
    try {
      this.exams = await apiFetch('/exams/mine/')
      if (this.exams.length) {
        this.examId = this.exams[0].id
        await this.load()
      }
    } catch (e) {
      this.error = e.message
      if (e.status === 401) this.$router.push('/login')
    } finally {
      this.loading = false
    }
  },
  watch: {
    examId() {
      this.load()
    },
  },
  computed: {
    maxWeekXp() {
      return Math.max(1, ...this.data.weeks.map((w) => w.xp))
    },
    curvePoints() {
      const pts = this.data?.readiness_curve || []
      if (pts.length < 2) return { line: '', dots: [] };
      const W = 560, H = 120, P = 8
      const n = pts.length
      const coords = pts.map((p, i) => [
        P + (i / Math.max(1, n - 1)) * (W - 2 * P),
        H - P - (Math.min(100, Math.max(0, p.predicted_pct)) / 100) * (H - 2 * P),
      ])
      return {
        line: coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' '),
        dots: coords.map(([x, y], i) => ({ x, y, label: `${pts[i].date}: ${pts[i].predicted_pct}%` })),
      }
    },
    trapBadges() {
      // Earned, not assigned: a triggered-then-quiet trap means the learner
      // fell for it, then stopped falling for it. That is the whole game.
      const list = this.data?.misconceptions || []
      return list
        .filter((m) => m.status === 'quiet' && m.triggered_count >= 1)
        .sort((a, b) => b.triggered_count - a.triggered_count)
        .slice(0, 12)
    },
  },
  methods: {
    async load() {
      if (!this.examId) return
      this.loading = true
      this.error = ''
      try {
        this.data = await apiFetch(`/practice/analytics/?exam_id=${this.examId}`)
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    examName(id) {
      const e = this.exams.find((x) => x.id === Number(id))
      return e ? e.name : `#${id}`
    },
    badgeClass(status) {
      if (status === 'open') return 'bg-red-100 text-red-700'
      if (status === 'quiet') return 'bg-amber-100 text-amber-800'
      return 'bg-slate-100 text-slate-500'
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-display text-2xl font-bold tracking-tight">Analytics</h2>
      <select v-if="exams.length" v-model="examId" class="rounded-2xl border border-slate-300 bg-white px-3 py-2 text-sm">
        <option v-for="e in exams" :key="e.id" :value="e.id">{{ e.name }}</option>
      </select>
    </div>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <p v-if="!exams.length && !loading" class="text-sm text-slate-500">Join an exam first — analytics appear once you start answering.</p>

    <template v-if="data">
      <h3 class="mb-2 mt-6 text-lg font-semibold">Readiness over time</h3>
      <div v-if="data.readiness_curve.length >= 2" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <svg viewBox="0 0 560 120" class="w-full">
          <line x1="8" y1="112" x2="552" y2="112" stroke="#e2e8f0" />
          <line x1="8" y1="62" x2="552" y2="62" stroke="#e2e8f0" stroke-dasharray="4 4" />
          <line x1="8" y1="12" x2="552" y2="12" stroke="#e2e8f0" />
          <path :d="curvePoints.line" fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linejoin="round" />
          <circle v-for="(d, i) in curvePoints.dots" :key="i" :cx="d.x" :cy="d.y" r="3.5" fill="#0f172a"><title>{{ d.label }}</title></circle>
        </svg>
        <p class="mt-1 text-xs text-slate-500">One point per active day. Gaps mean rest days, not lost data.</p>
      </div>
      <p v-else class="text-sm text-slate-500">Answer questions on more days and your readiness curve will draw itself here.</p>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Last 8 weeks</h3>
      <div class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div v-for="w in data.weeks" :key="w.week_start" class="mb-2 flex items-center gap-3 text-xs">
          <span class="w-24 shrink-0 text-slate-500">{{ w.week_start }}</span>
          <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100">
            <div class="h-full rounded-full bg-slate-900" :style="{ width: `${Math.round((w.xp / maxWeekXp) * 100)}%` }"></div>
          </div>
          <span class="w-28 shrink-0 text-right tabular-nums">{{ w.xp }} XP · {{ w.answered }} answered</span>
        </div>
      </div>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Topics</h3>
      <div class="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead>
            <tr class="border-b border-slate-200 text-xs text-slate-500">
              <th class="px-4 py-2">Topic</th>
              <th class="px-4 py-2">Mastery</th>
              <th class="px-4 py-2">Answered</th>
              <th class="px-4 py-2">Accuracy</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in data.topics" :key="t.topic_id" class="border-b border-slate-100 last:border-0">
              <td class="px-4 py-2 font-medium">{{ t.name }}</td>
              <td class="px-4 py-2 tabular-nums">{{ Math.round(t.mastery_p * 100) }}%</td>
              <td class="px-4 py-2 tabular-nums">{{ t.attempts }}</td>
              <td class="px-4 py-2 tabular-nums">{{ t.accuracy == null ? '—' : `${t.accuracy}%` }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Trap-slayer badges</h3>
      <p v-if="!trapBadges.length" class="text-sm text-slate-500">No badges yet — trip a trap, then stop tripping it. That's the whole game.</p>
      <div v-else class="flex flex-wrap gap-2">
        <span v-for="m in trapBadges" :key="m.id" :title="`${m.description} — tripped ${m.triggered_count}×, now quiet`" class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-800">
          ★ Trap slayer · {{ m.topic_name }}
        </span>
      </div>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Misconception ledger</h3>
      <p v-if="!data.misconceptions.length" class="text-sm text-slate-500">No misconceptions mapped for this exam yet.</p>
      <div v-for="m in data.misconceptions" :key="m.id" class="mb-2 rounded-3xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <div class="flex items-center justify-between gap-2">
          <p class="font-medium">{{ m.description }}</p>
          <span class="shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold" :class="badgeClass(m.status)">{{ m.status }}</span>
        </div>
        <p class="mt-1 text-xs text-slate-500">{{ m.topic_name }} · tripped {{ m.triggered_count }}× · {{ m.correct_since }} correct since</p>
        <router-link v-if="m.status === 'open'" :to="`/practice/${examId}`" class="mt-2 inline-block rounded-full bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-700">Retest this trap →</router-link>
      </div>

      <h3 class="mb-2 mt-6 text-lg font-semibold">Room history</h3>
      <p v-if="!data.rooms.length" class="text-sm text-slate-500">No rooms joined yet — find one under the Rooms tab.</p>
      <div v-for="r in data.rooms" :key="r.room_id" class="mb-2 rounded-3xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <router-link :to="`/rooms/${r.room_id}`" class="font-medium text-slate-900 hover:underline">{{ r.name || `Room #${r.room_id}` }}</router-link>
        <span class="ml-2 text-xs text-slate-500">{{ r.status }} · #{{ r.rank }} of {{ r.participants }} · {{ r.user_xp }} XP · {{ r.user_accuracy }}%</span>
      </div>
    </template>
  </div>
</template>
