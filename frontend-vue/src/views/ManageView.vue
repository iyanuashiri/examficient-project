<script>
import { apiFetch } from '@/api/client.js'

export default {
  data() {
    return {
      exam: null,
      syllabi: [],
      topics: [],
      questions: [],
      error: '',
      loading: true,
      tab: 'questions',
      // syllabus form
      newVersion: '',
      syMsg: '',
      // topics bulk form
      topicsText: '',
      topicsMsg: '',
      // question form
      qStem: '',
      qExplanation: '',
      qTopicId: '',
      qSyllabusId: '',
      qOptions: [
        { content: '', is_correct: true, explanation: '' },
        { content: '', is_correct: false, explanation: '' },
      ],
      qMsg: '',
    }
  },
  computed: {
    id() {
      return this.$route.params.id
    },
    topicName() {
      return (id) => (this.topics.find((t) => t.id === Number(id)) || {}).name || `#${id}`
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
        this.exam = await apiFetch(`/exams/${this.id}/`)
        this.syllabi = await apiFetch(`/exams/${this.id}/syllabi/`)
        const current = this.syllabi.find((s) => s.is_current) || this.syllabi[0]
        this.topics = current ? await apiFetch(`/syllabi/${current.id}/topics/`) : []
        this.questions = await apiFetch(`/exams/${this.id}/questions/?limit=100`)
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async addSyllabus() {
      this.syMsg = ''
      try {
        const s = await apiFetch(`/exams/${this.id}/syllabi/`, {
          method: 'POST',
          body: { version_label: this.newVersion },
        })
        this.syllabi.push(s)
        this.newVersion = ''
        this.syMsg = 'Added. New revisions never edit old ones.'
      } catch (e) {
        this.syMsg = e.message
      }
    },
    async bulkTopics() {
      this.topicsMsg = ''
      try {
        const current = this.syllabi.find((s) => s.is_current) || this.syllabi[0]
        if (!current) {
          this.topicsMsg = 'Create a syllabus first.'
          return
        }
        const items = this.topicsText
          .split('\n')
          .map((l) => l.trim())
          .filter(Boolean)
          .map((line, i) => {
            const [code, ...rest] = line.split('|')
            const name = (rest.join('|') || code).trim()
            return { code: rest.length ? code.trim() : null, name, sort_order: i }
          })
        const rows = await apiFetch(`/syllabi/${current.id}/topics/bulk/`, {
          method: 'PUT',
          body: items,
        })
        this.topics = await apiFetch(`/syllabi/${current.id}/topics/`)
        this.topicsText = ''
        this.topicsMsg = `Upserted ${rows.length} topics (matched by code).`
      } catch (e) {
        this.topicsMsg = e.message
      }
    },
    addOption() {
      // No letters: the player assigns A/B/C… after shuffling.
      this.qOptions.push({ content: '', is_correct: false, explanation: '' })
    },
    async addQuestion() {
      this.qMsg = ''
      try {
        const q = await apiFetch(`/exams/${this.id}/questions/`, {
          method: 'POST',
          body: {
            syllabus_id: this.qSyllabusId === '' ? null : Number(this.qSyllabusId),
            primary_topic_id: this.qTopicId === '' ? null : Number(this.qTopicId),
            stem: this.qStem,
            explanation: this.qExplanation || null,
            options: this.qOptions
              .filter((o) => o.content.trim() !== '')
              .map((o) => ({ content: o.content, is_correct: !!o.is_correct, explanation: o.explanation || null })),
          },
        })
        this.questions.unshift(q)
        this.qStem = ''
        this.qExplanation = ''
        this.qOptions = [
          { content: '', is_correct: true, explanation: '' },
          { content: '', is_correct: false, explanation: '' },
        ]
        this.qMsg = `Question #${q.id} live.`
      } catch (e) {
        this.qMsg = e.message
      }
    },
  },
}
</script>

<template>
  <div>
    <router-link :to="`/exams/${this.id}`" class="text-sm text-slate-500 hover:text-slate-900">← back</router-link>
    <h2 class="mb-4 mt-2 font-display text-2xl font-bold tracking-tight">Manage content</h2>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <div class="mb-4 flex gap-2">
      <button v-for="t in ['questions', 'topics', 'syllabus']" :key="t" @click="tab = t"
        class="rounded-full px-4 py-1.5 text-sm font-semibold" :class="tab === t ? 'bg-slate-900 text-white' : 'border border-slate-300 hover:bg-slate-50'">
        {{ t[0].toUpperCase() + t.slice(1) }} ({{ t === 'questions' ? questions.length : t === 'topics' ? topics.length : syllabi.length }})
      </button>
    </div>

    <div v-if="tab === 'syllabus'" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <ul class="mb-3 space-y-1 text-sm">
        <li v-for="s in syllabi" :key="s.id">{{ s.version_label }} <span v-if="s.is_current" class="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">current</span></li>
      </ul>
      <form @submit.prevent="addSyllabus" class="flex gap-2">
        <input v-model="newVersion" required placeholder="e.g. 2026" class="rounded-2xl border border-slate-300 px-3 py-2 text-sm" />
        <button type="submit" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">New revision</button>
      </form>
      <p v-if="syMsg" class="mt-2 text-sm text-slate-500">{{ syMsg }}</p>
    </div>

    <div v-if="tab === 'topics'" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p class="mb-2 text-sm text-slate-500">One per line: <code>CODE | Name</code> (code optional, matched for updates).</p>
      <textarea v-model="topicsText" rows="6" placeholder="G.1 | Genetics&#10;G.2 | Cell division" class="w-full rounded-2xl border border-slate-300 p-3 font-mono text-sm"></textarea>
      <button @click="bulkTopics" class="mt-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">Bulk upsert</button>
      <p v-if="topicsMsg" class="mt-2 text-sm text-slate-500">{{ topicsMsg }}</p>
      <ul class="mt-3 space-y-1 text-sm">
        <li v-for="t in topics" :key="t.id"><span class="text-slate-400">{{ t.code }}</span> {{ t.name }}</li>
      </ul>
    </div>

    <div v-if="tab === 'questions'">
      <div class="mb-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p class="mb-3 text-sm font-semibold tracking-widest text-slate-400">ADD QUESTION</p>
        <label class="mb-2 block text-sm font-medium">Stem
          <textarea v-model="qStem" rows="2" required class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2"></textarea>
        </label>
        <div class="mb-2 grid grid-cols-2 gap-2">
          <label class="text-sm font-medium">Syllabus
            <select v-model="qSyllabusId" class="mt-1 block w-full rounded-2xl border border-slate-300 px-2 py-1.5">
              <option value="">—</option>
              <option v-for="s in syllabi" :key="s.id" :value="s.id">{{ s.version_label }}</option>
            </select>
          </label>
          <label class="text-sm font-medium">Primary topic
            <select v-model="qTopicId" class="mt-1 block w-full rounded-2xl border border-slate-300 px-2 py-1.5">
              <option value="">—</option>
              <option v-for="t in topics" :key="t.id" :value="t.id">{{ t.code ? `${t.code} — ` : '' }}{{ t.name }}</option>
            </select>
          </label>
        </div>
        <label class="mb-2 block text-sm font-medium">Authored explanation
          <textarea v-model="qExplanation" rows="2" class="mt-1 block w-full rounded-2xl border border-slate-300 px-3 py-2"></textarea>
        </label>
        <div v-for="(o, i) in qOptions" :key="i" class="mb-2 grid grid-cols-[auto_1fr_auto] items-start gap-2 rounded-2xl border border-slate-200 p-2">
          <span class="px-1 font-bold">{{ 'ABCD'[i] || `#${i + 1}` }}</span>
          <div>
            <input v-model="o.content" placeholder="Option text" class="w-full rounded border border-slate-200 px-2 py-1 text-sm" />
            <input v-model="o.explanation" placeholder="Why this option is right/wrong (shown after answering)" class="mt-1 w-full rounded border border-slate-200 px-2 py-1 text-sm" />
          </div>
          <label class="flex items-center gap-1 text-xs">correct <input v-model="o.is_correct" type="checkbox" /></label>
        </div>
        <div class="flex gap-2">
          <button @click="addOption" type="button" class="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold hover:bg-slate-50">+ option</button>
          <button @click="addQuestion" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">Save question</button>
        </div>
        <p v-if="qMsg" class="mt-2 text-sm text-slate-500">{{ qMsg }}</p>
      </div>

      <div v-for="q in questions" :key="q.id" class="mb-2 rounded-3xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
        <p class="font-medium">{{ q.stem }}</p>
        <p class="mt-1 text-xs text-slate-500">
          {{ q.options.map((o, i) => (o.is_correct ? 'ABCD'[i] || `#${i + 1}` : null)).filter(Boolean).join(', ') || 'none' }} correct
          {{ q.primary_topic_id ? ` · ${topicName(q.primary_topic_id)}` : '' }}
          {{ q.difficulty != null ? ` · b=${q.difficulty.toFixed(2)}` : '' }}
        </p>
      </div>
    </div>
  </div>
</template>
