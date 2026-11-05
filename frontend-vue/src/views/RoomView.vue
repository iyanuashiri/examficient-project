<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      room: null,
      stats: null,
      board: null,
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
    try {
      const [room, stats, board] = await Promise.all([
        apiFetch(`/rooms/${this.id}/`),
        apiFetch(`/rooms/${this.id}/stats/`),
        apiFetch(`/rooms/${this.id}/leaderboard/?limit=10`),
      ])
      this.room = room
      this.stats = stats
      this.board = board
    } catch (e) {
      this.error = e.message
    } finally {
      this.loading = false
    }
  },
}
</script>

<template>
  <div>
    <router-link to="/rooms" class="text-sm text-slate-500 hover:text-slate-900">← Rooms</router-link>
    <p v-if="loading" class="mt-2 text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <template v-if="room && stats">
      <p class="mt-2 inline-block rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">{{ stats.status.toUpperCase() }}</p>
      <h2 class="mt-2 font-display text-3xl font-bold tracking-tight">{{ room.name || `Room #${room.id}` }}</h2>
      <p class="text-sm text-slate-500">
        {{ room.exam_name }} · share this link to invite people ·
        {{ new Date(room.starts_at).toLocaleString() }} → {{ new Date(room.ends_at).toLocaleString() }}
      </p>
      <p class="mt-1 text-xs text-slate-400">No sign-up needed — answer questions before the window closes to join the room.</p>
      <div class="mt-4 grid grid-cols-2 gap-3 text-center">
        <div class="rounded-3xl border border-slate-200 bg-white p-4"><p class="font-display text-2xl font-bold">{{ stats.participants }}</p><p class="text-xs text-slate-500">in the room</p></div>
        <div class="rounded-3xl border border-slate-200 bg-white p-4"><p class="font-display text-2xl font-bold">{{ board && board.me ? `#${board.me.rank}` : '—' }}</p><p class="text-xs text-slate-500">your rank</p></div>
      </div>
      <div v-if="board && board.entries.length" class="mt-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex items-center justify-between">
          <p class="text-sm font-semibold tracking-widest text-slate-400">LEADERBOARD</p>
          <router-link :to="`/rooms/${room.id}/board`" class="text-xs font-semibold text-slate-900 hover:underline">Full board →</router-link>
        </div>
        <ul class="mt-2 space-y-1 text-sm">
          <li v-for="e in board.entries" :key="e.rank" class="flex justify-between" :class="board.me && e.rank === board.me.rank ? 'font-bold' : ''">
            <span>{{ e.rank }}. {{ e.display_name }}</span><span class="tabular-nums">{{ e.xp }} XP</span>
          </li>
        </ul>
      </div>
      <div v-if="board && !board.entries.length" class="mt-4 rounded-3xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
        No scores yet — be the first to answer inside this window.
        <router-link :to="`/practice/${room.exam_id}`" class="font-semibold text-slate-900 hover:underline">Start answering →</router-link>
      </div>
      <div v-if="stats.hardest_questions.length" class="mt-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold tracking-widest text-slate-400">HARDEST RIGHT NOW</p>
        <ul class="mt-2 space-y-2 text-sm">
          <li v-for="q in stats.hardest_questions" :key="q.question_id">
            {{ q.stem }} <span class="text-slate-500">({{ Math.round(q.correct_rate * 100) }}% correct, {{ q.attempts }} tries)</span>
          </li>
        </ul>
      </div>
      <p v-if="stats.top_trap" class="mt-4 rounded-3xl bg-amber-50 p-4 text-sm text-amber-800">Room trap: {{ stats.top_trap }}</p>
    </template>
  </div>
</template>
