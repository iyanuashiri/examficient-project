<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      rooms: [],
      official: [],
      exams: [],
      showCreate: false,
      error: '',
      loading: true,
      newExam: '',
      newName: '',
      newStarts: '',
      newHours: 2,
      msg: '',
    }
  },
  async created() {
    await this.load()
  },
  methods: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const [mine, official, exams] = await Promise.all([
          apiFetch('/rooms/mine/'),
          apiFetch('/rooms/official/'),
          apiFetch('/exams/mine/'),
        ])
        this.rooms = mine
        this.official = official
        this.exams = exams
        this.newExam = exams.length ? exams[0].id : ''
      } catch (e) {
        this.error = e.message
        if (e.status === 401) this.$router.push('/login')
      } finally {
        this.loading = false
      }
    },
    async create() {
      this.msg = ''
      try {
        const now = new Date()
        const end = new Date(now.getTime() + Number(this.newHours) * 3600000)
        const room = await apiFetch('/rooms/', {
          method: 'POST',
          body: { exam_id: Number(this.newExam), name: this.newName || null, starts_at: now.toISOString(), ends_at: end.toISOString() },
        })
        this.$router.push(`/rooms/${room.id}`)
      } catch (e) {
        this.msg = e.message
      }
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-display text-2xl font-bold tracking-tight">Drill rooms</h2>
      <button @click="showCreate = !showCreate" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">
        {{ showCreate ? 'Close' : '+ New room' }}
      </button>
    </div>

    <div v-if="showCreate" class="mb-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p class="mb-3 font-semibold">New room (starts now)</p>
      <form @submit.prevent="create" class="grid max-w-md grid-cols-2 gap-3 text-sm">
        <label class="font-medium">Exam
          <select v-model="newExam" class="mt-1 block w-full rounded-2xl border border-slate-300 px-2 py-1.5">
            <option v-for="e in exams" :key="e.id" :value="e.id">{{ e.name }}</option>
          </select>
        </label>
        <label class="font-medium">Length (hrs)
          <input v-model="newHours" type="number" min="1" max="12" class="mt-1 block w-full rounded-2xl border border-slate-300 px-2 py-1.5" />
        </label>
        <label class="col-span-2 font-medium">Name (optional)
          <input v-model="newName" placeholder="Evening drill" class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2" />
        </label>
        <button type="submit" class="col-span-2 rounded-full bg-slate-900 px-4 py-2.5 font-semibold text-white hover:bg-slate-700">Create room</button>
      </form>
      <p v-if="msg" class="mt-2 text-sm text-slate-500">{{ msg }}</p>
    </div>

    <h3 class="mb-2 text-lg font-semibold">Official mocks</h3>
    <p v-if="!official.length && !loading" class="text-sm text-slate-500">No official rooms scheduled yet — check back soon.</p>
    <div class="grid gap-3 sm:grid-cols-2">
      <router-link v-for="r in official" :key="r.id" :to="`/rooms/${r.id}`" class="rounded-3xl border-2 border-slate-900 bg-white p-4 shadow-sm transition hover:shadow-md">
        <p class="font-display font-bold">{{ r.name || `Room #${r.id}` }} <span class="ml-1 rounded-full bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white">OFFICIAL</span></p>
        <p class="mt-1 text-xs text-slate-500">{{ r.exam_name }} · {{ new Date(r.starts_at).toLocaleString() }}</p>
      </router-link>
    </div>

    <h3 class="mb-2 mt-6 text-lg font-semibold">Yours</h3>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <div class="grid gap-3 sm:grid-cols-2">
      <router-link v-for="r in rooms" :key="r.id" :to="`/rooms/${r.id}`" class="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400">
        <p class="font-display font-bold">{{ r.name || `Room #${r.id}` }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ r.exam_name }}  · {{ new Date(r.starts_at).toLocaleString() }}</p>
      </router-link>
    </div>
    <p v-if="!rooms.length && !loading" class="text-sm text-slate-500">No rooms yet — hit + New room above.</p>
  </div>
</template>
