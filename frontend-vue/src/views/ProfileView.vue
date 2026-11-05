<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      user: null,
      optOut: false,
      error: '',
      msg: '',
      loading: true,
    }
  },
  async created() {
    try {
      this.user = await apiFetch('/users/me/')
      this.optOut = !this.user.show_on_leaderboard
    } catch (e) {
      this.error = e.message
      if (e.status === 401) this.$router.push('/login')
    } finally {
      this.loading = false
    }
  },
  methods: {
    async save() {
      this.msg = ''
      this.error = ''
      try {
        this.user = await apiFetch('/users/me/', {
          method: 'PATCH',
          body: { show_on_leaderboard: !this.optOut },
        })
        this.msg = 'Saved.'
      } catch (e) {
        this.error = e.message
      }
    },
  },
}
</script>

<template>
  <div>
    <h2 class="mb-4 font-display text-2xl font-bold tracking-tight">Profile</h2>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <template v-if="user">
      <div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="font-display text-xl font-bold">{{ user.first_name }} {{ user.last_name }}</p>
        <p class="mt-1 text-sm text-slate-500">{{ user.email }} · {{ user.role }}</p>
        <label class="mt-4 flex items-center gap-2 text-sm">
          <input v-model="optOut" type="checkbox" /> Hide me from leaderboards
        </label>
        <button @click="save" class="mt-3 rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-700">Save</button>
        <p v-if="msg" class="mt-2 text-sm text-emerald-700">{{ msg }}</p>
      </div>
    </template>
  </div>
</template>
