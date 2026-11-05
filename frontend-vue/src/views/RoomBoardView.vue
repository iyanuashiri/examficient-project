<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      board: null,
      name: '',
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
      const [room, board] = await Promise.all([
        apiFetch(`/rooms/${this.id}/`),
        apiFetch(`/rooms/${this.id}/leaderboard/?limit=100`),
      ])
      this.name = room.name || `Room #${room.id}`
      this.board = board
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
    <router-link :to="`/rooms/${id}`" class="text-sm text-slate-500 hover:text-slate-900">← Back to room</router-link>
    <h2 class="mb-1 mt-2 font-display text-2xl font-bold tracking-tight">Leaderboard</h2>
    <p v-if="name" class="mb-4 text-sm text-slate-500">{{ name }}</p>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <div v-if="board" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p v-if="!board.entries.length" class="text-sm text-slate-500">No scores yet — be the first to answer in this room.</p>
      <ul class="space-y-1 text-sm">
        <li v-for="e in board.entries" :key="e.rank" class="flex items-center justify-between rounded-xl px-2 py-1.5" :class="board.me && e.rank === board.me.rank ? 'bg-slate-900 font-semibold text-white' : 'odd:bg-slate-50'">
          <span class="tabular-nums">#{{ e.rank }} · {{ e.display_name }}</span>
          <span class="tabular-nums">{{ e.xp }} XP · {{ e.questions }} answered</span>
        </li>
      </ul>
      <p v-if="board.me" class="mt-3 text-sm text-slate-600">You're #{{ board.me.rank }} with {{ board.me.xp }} XP.</p>
    </div>
  </div>
</template>
