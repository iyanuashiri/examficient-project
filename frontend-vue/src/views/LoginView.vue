<script>
import { apiFetch, setToken } from '@/api/client.js'

export default {
  data() {
    return {
      email: '',
      password: '',
      error: '',
      loading: false,
    }
  },
  methods: {
    async submit() {
      this.error = ''
      this.loading = true
      try {
        const data = await apiFetch('/auth/login/', {
          method: 'POST',
          auth: false,
          form: true,
          body: { email: this.email, password: this.password },
        })
        setToken(data.access_token)
        this.$router.push(this.$route.query.redirect || '/home')
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<template>
  <div class="mx-auto max-w-sm">
    <h2 class="mb-4 font-display text-3xl font-bold tracking-tight">Login</h2>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>
    <form @submit.prevent="submit" class="space-y-3">
      <label class="block text-sm font-medium">Email
        <input v-model="email" type="email" required class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2.5" />
      </label>
      <label class="block text-sm font-medium">Password
        <input v-model="password" type="password" required class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2.5" />
      </label>
      <button type="submit" :disabled="loading" class="w-full rounded-full bg-slate-900 px-3 py-2.5 font-semibold text-white hover:bg-slate-700 disabled:opacity-50">Login</button>
    </form>
    <p class="mt-4 text-sm text-slate-500">No account? <router-link to="/register" class="font-medium text-slate-900 hover:underline">Register</router-link></p>
  </div>
</template>
