<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      featured: [],
      mine: [],
      error: '',
      loading: true,
      showCreate: false,
      newCode: '',
      newName: '',
      newPassMark: '',
      newExamDate: '',
      createError: '',
    }
  },
  async created() {
    try {
      const [featured, mine] = await Promise.all([
        apiFetch('/exams/featured/'),
        apiFetch('/exams/mine/'),
      ])
      this.featured = featured
      this.mine = mine
    } catch (e) {
      this.error = e.message
      if (e.status === 401) this.$router.push('/login')
    } finally {
      this.loading = false
    }
  },
  computed: {
    mineCodes() {
      return new Set(this.mine.map((e) => e.code))
    },
  },
  methods: {
    async createExam() {
      this.createError = ''
      try {
        const exam = await apiFetch('/exams/', {
          method: 'POST',
          body: {
            code: this.newCode,
            name: this.newName,
            visibility: 'private',
            pass_mark: this.newPassMark === '' ? null : Number(this.newPassMark),
            exam_date: this.newExamDate === '' ? null : this.newExamDate,
          },
        })
        this.mine.push(exam)
        this.newCode = ''
        this.newName = ''
        this.newPassMark = ''
        this.newExamDate = ''
        this.showCreate = false
      } catch (e) {
        this.createError = e.message
      }
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h2 class="font-display text-2xl font-bold tracking-tight">Exams</h2>
      <button @click="showCreate = !showCreate" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">
        {{ showCreate ? 'Close' : '+ New exam' }}
      </button>
    </div>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <div v-if="showCreate" class="mb-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p class="mb-3 font-semibold">New private exam</p>
      <p v-if="createError" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ createError }}</p>
      <form @submit.prevent="createExam" class="grid grid-cols-2 gap-3">
        <label class="block text-sm font-medium">Code
          <input v-model="newCode" required class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Name
          <input v-model="newName" required class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Pass mark % <span class="font-normal text-slate-400">(optional)</span>
          <input v-model="newPassMark" type="number" min="0" max="100" step="0.1" class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">Exam date <span class="font-normal text-slate-400">(optional)</span>
          <input v-model="newExamDate" type="date" class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2" />
        </label>
        <button type="submit" class="col-span-2 rounded-full bg-slate-900 px-4 py-2.5 font-semibold text-white hover:bg-slate-700">Create</button>
      </form>
    </div>

    <h3 class="mb-2 text-lg font-semibold">My exams</h3>
    <p v-if="!mine.length && !loading" class="text-sm text-slate-500">Nothing here yet — hit <strong>+ New exam</strong> above.</p>
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <router-link v-for="exam in mine" :key="exam.code" :to="`/exams/${exam.id}`" class="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400">
        <p class="font-display font-bold">{{ exam.name }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ exam.code }} · {{ exam.status }}</p>
      </router-link>
    </div>

    <h3 class="mb-2 mt-8 text-lg font-semibold">Featured</h3>
    <p v-if="!featured.length && !loading" class="text-sm text-slate-500">No featured exams yet.</p>
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <router-link v-for="exam in featured" :key="exam.code" :to="`/exams/${exam.id}`" class="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-400">
        <p class="font-display font-bold">{{ exam.name }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ exam.code }}
          <span v-if="mineCodes.has(exam.code)" class="ml-1 rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-700">Enrolled</span>
        </p>
      </router-link>
    </div>
  </div>
</template>
