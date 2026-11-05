<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      user: null,
      exams: [],
      cards: [],
      nudgeText: null,
      error: '',
      loading: true,
    }
  },
  computed: {
    nudge() {
      // The exam that most needs you today: actionable plan, nearest deadline first.
      const actionable = this.cards.filter((c) => c.plan && c.plan.minutes_per_day != null);
      if (!actionable.length) return null;
      actionable.sort((a, b) => (a.plan.days_left ?? 9999) - (b.plan.days_left ?? 9999));
      return actionable[0];
    },
  },
  methods: {
    async refreshNudgeText() {
      // Narrated upgrade of the template note; any failure keeps the note.
      const n = this.nudge
      if (!n || !n.plan || n.plan.minutes_per_day == null) return
      try {
        const kind = n.plan.feasible === false ? 'replan' : 'plan_intro'
        const r = await apiFetch('/practice/narrate/', {
          method: 'POST',
          body: { kind, exam_id: n.exam.id, context: {} },
        })
        if (r && r.text) this.nudgeText = r.text
      } catch { /* template note stands */ }
    },
  },
  async created() {
    try {
      const [user, mine] = await Promise.all([
        apiFetch('/users/me/'),
        apiFetch('/exams/mine/'),
      ])
      this.user = user
      this.exams = mine
      this.cards = await Promise.all(
        this.exams.map(async (e) => {
          try {
            const [readiness, stats, board, plan] = await Promise.all([
              apiFetch(`/practice/readiness/?exam_id=${e.id}`),
              apiFetch(`/practice/stats/?exam_id=${e.id}`),
              apiFetch(`/practice/leaderboard/?exam_id=${e.id}`),
              apiFetch(`/practice/plan/?exam_id=${e.id}`),
            ])
            return { exam: e, readiness, stats, board, plan }
          } catch {
            return { exam: e, readiness: null, stats: null, board: null, plan: null }
          }
        }),
      )
      this.refreshNudgeText()
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
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <template v-if="user">
      <h2 class="font-display text-3xl font-bold tracking-tight">Hi, {{ user.first_name }}.</h2>
      <p class="mt-1 text-slate-500">Pick up where you left off.</p>

      <div v-if="nudge" class="mt-4 rounded-3xl bg-slate-900 p-5 text-slate-200 shadow-sm">
        <p class="text-xs font-semibold tracking-widest text-slate-400">TODAY'S FOCUS · {{ nudge.exam.name.toUpperCase() }}</p>
        <p class="mt-1 text-sm">{{ nudgeText || nudge.plan.note }}</p>
        <ul v-if="nudge.plan.focus_topics.length" class="mt-2 space-y-1 text-sm text-slate-300">
          <li v-for="t in nudge.plan.focus_topics" :key="t.topic_id">• {{ t.name }} — {{ t.points_share_pct }}% of your gap</li>
        </ul>
        <router-link :to="`/practice/${nudge.exam.id}`" class="mt-3 inline-block rounded-full bg-white px-5 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-200">Start today's session →</router-link>
      </div>

      <div class="mt-6 grid gap-3 sm:grid-cols-2">
        <div v-for="c in cards" :key="c.exam.id" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <router-link :to="`/exams/${c.exam.id}`" class="font-display text-lg font-bold hover:underline">{{ c.exam.name }}</router-link>
          <template v-if="c.readiness">
            <p class="mt-2 font-display text-4xl font-bold">{{ c.readiness.predicted_score_pct }}<span class="text-lg text-slate-400">%</span></p>
            <p class="text-xs text-slate-500">
              {{ c.readiness.topics_attempted }}/{{ c.readiness.topics_total }} topics
              <span v-if="c.readiness.pass_mark != null"> · {{ c.readiness.on_track ? 'clear to pass' : `${c.readiness.points_to_pass} to pass` }}</span>
            </p>
            <p v-if="c.stats" class="mt-1 text-xs text-slate-500">{{ c.stats.streak_days }}-day streak · {{ c.stats.xp_week }} XP this week · {{ c.stats.level }}</p>
            <p v-if="c.board && c.board.me" class="mt-1 text-xs font-semibold text-slate-600">League #{{ c.board.me.rank }} · {{ c.board.me.xp }} XP</p>
            <router-link :to="`/practice/${c.exam.id}`" class="mt-3 inline-block rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-700">Continue →</router-link>
          </template>
          <p v-else class="mt-2 text-sm text-slate-500">Not started — take the first calibration.</p>
        </div>
      </div>
    </template>
  </div>
</template>
