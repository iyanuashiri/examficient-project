<script>
import { apiFetch } from '@/api/client.js'
import { VOICE_SUPPORTED, startRecording } from '@/api/voice.js'

export default {
  data() {
    return {
      question: null,
      chosen: null,
      result: null,
      plan: null,
      mission: null,
      error: '',
      loading: true,
      submitting: false,
      done: false,
      receivedAt: 0,
      elapsed: 0,
      ticker: null,
      answered: 0,
      correctCount: 0,
      shuffled: [],
      showExplain: false,
      explainText: '',
      explainResult: null,
      explaining: false,
      voiceSupported: VOICE_SUPPORTED,
      examVoice: false,
      recorder: null,
      listeningVoice: false,
      transcribingVoice: false,
    }
  },
  computed: {
    id() {
      return this.$route.params.id
    },
    accuracy() {
      return this.answered === 0 ? null : Math.round((this.correctCount / this.answered) * 100)
    },
    resultOptions() {
      // Re-attach the letters the user actually saw (matched by stable id).
      if (!this.result || !this.result.options) return []
      return this.result.options.map((o) => {
        const seen = this.shuffled.find((s) => s.id === o.id)
        return { ...o, letter: seen ? seen.letter : '?' }
      })
    },
    correctLetter() {
      if (!this.result || this.result.correct_option_id == null) return null
      const seen = this.shuffled.find((s) => s.id === this.result.correct_option_id)
      return seen ? seen.letter : null
    },
  },
  async created() {
    try {
      const exam = await apiFetch(`/exams/${this.id}/`)
      this.examVoice = !!(exam && exam.voice_enabled)
    } catch {
      // exam meta is a nice-to-have; practice works without it
    }
    try {
      this.plan = await apiFetch(`/practice/plan/?exam_id=${this.id}`)
      if (this.plan && this.plan.minutes_per_day != null) {
        // Narrated mission upgrades the template note; failure keeps the note.
        const feasible = this.plan.feasible !== false
        apiFetch('/practice/narrate/', {
          method: 'POST',
          body: { kind: feasible ? 'plan_intro' : 'replan', exam_id: Number(this.id), context: {} },
        }).then((r) => { this.mission = r.text }).catch(() => {})
      }
    } catch {
      // plan is a nice-to-have; the loop works without it
    }
    await this.next()
  },
  beforeUnmount() {
    this.stopTicker()
  },
  methods: {
    shuffleOptions() {
      // Letters are presentation: shuffle once per question, assign A/B/C….
      // Grading and diagnosis key off option ids, so order can never corrupt them.
      const arr = (this.question?.options || []).map((o) => ({ ...o }))
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      this.shuffled = arr.map((o, i) => ({ ...o, letter: 'ABCD'[i] || `O${i + 1}` }))
    },
    stopTicker() {
      if (this.ticker) {
        clearInterval(this.ticker)
        this.ticker = null
      }
    },
    startTicker() {
      this.stopTicker()
      this.receivedAt = Date.now()
      this.elapsed = 0
      this.ticker = setInterval(() => {
        this.elapsed = Math.floor((Date.now() - this.receivedAt) / 1000)
      }, 1000)
    },
    async next() {
      this.loading = true
      this.error = ''
      this.chosen = null
      this.result = null
      this.showExplain = false
      this.explainText = ''
      this.explainResult = null
      this.recorder = null
      this.listeningVoice = false
      try {
        const q = await apiFetch(`/practice/next/?exam_id=${this.id}`)
        this.question = q
        this.done = !q
        if (q) {
          this.shuffleOptions()
          this.startTicker()
        } else this.stopTicker()
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },
    async submit() {
      if (this.chosen === null || this.chosen === undefined) return
      this.submitting = true
      this.error = ''
      const response_ms = Date.now() - this.receivedAt
      try {
        this.result = await apiFetch('/practice/answer/', {
          method: 'POST',
          body: { question_id: this.question.id, chosen_option_id: Number(this.chosen), response_ms },
        })
        this.stopTicker()
        this.answered += 1
        if (this.result.correct) this.correctCount += 1
      } catch (e) {
        this.error = e.message
      } finally {
        this.submitting = false
      }
    },
    async dictate() {
      // Voice input via Meta Muse Voice Transcribe (see ChallengeView for the flow).
      if (this.listeningVoice && this.recorder) {
        const rec = this.recorder
        this.listeningVoice = false
        this.transcribingVoice = true
        this.error = ''
        try {
          const wav = await rec.stop()
          const fd = new FormData()
          fd.append('file', wav, 'audio.wav')
          const r = await apiFetch('/practice/transcribe/', { method: 'POST', body: fd, raw: true, timeoutMs: 90000 })
          this.explainText = (this.explainText ? this.explainText + ' ' : '') + r.transcript
        } catch (e) {
          this.error = e.message
        } finally {
          this.transcribingVoice = false
          this.recorder = null
        }
        return
      }
      if (this.transcribingVoice) return
      try {
        this.recorder = await startRecording()
        this.listeningVoice = true
      } catch (e) {
        this.error = e.message || 'Microphone unavailable.'
      }
    },
    async submitExplain() {
      if (!this.explainText.trim() || this.explaining) return
      this.explaining = true
      this.error = ''
      try {
        this.explainResult = await apiFetch('/practice/explain/', {
          method: 'POST',
          body: { question_id: this.question.id, text: this.explainText.trim() },
        })
      } catch (e) {
        this.error = e.message
      } finally {
        this.explaining = false
      }
    },
  },
}
</script>

<template>
  <div>
    <router-link :to="`/exams/${this.id}`" class="text-sm text-slate-500 hover:text-slate-900">← back</router-link>
    <div class="mb-4 mt-2 flex items-end justify-between">
      <h2 class="font-display text-2xl font-bold tracking-tight">Practice</h2>
      <p v-if="answered > 0" class="text-sm text-slate-500">
        Session: {{ correctCount }}/{{ answered }}{{ accuracy !== null ? ` · ${accuracy}%` : '' }}
      </p>
    </div>
    <div v-if="plan && plan.minutes_per_day != null" class="mb-4 rounded-3xl bg-slate-900 p-4 text-sm text-slate-200">
      <span class="font-semibold text-white">Today's mission:</span> {{ mission || plan.note }}
    </div>
    <p v-if="loading" class="text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <div v-if="done && !loading" class="rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <p class="font-display text-4xl font-bold">{{ accuracy !== null ? `${accuracy}%` : '—' }}</p>
      <p class="mt-1 text-sm text-slate-500">{{ correctCount }} of {{ answered }} correct this session</p>
      <router-link :to="`/exams/${this.id}`" class="mt-5 inline-block rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Back to exam</router-link>
    </div>

    <div v-if="question && !done" class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div class="mb-3 flex items-center justify-between text-xs text-slate-400">
        <span class="rounded-full bg-slate-100 px-3 py-1 font-semibold">{{ question.primary_topic_id ? `Topic ${question.primary_topic_id}` : 'Mixed' }}</span>
        <span class="tabular-nums">{{ elapsed }}s</span>
      </div>
      <p class="mb-4 text-lg font-medium">{{ question.stem }}</p>
      <form @submit.prevent="submit" class="space-y-2">
        <label v-for="opt in shuffled" :key="opt.id" class="flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 p-3 transition hover:border-slate-400" :class="chosen == opt.id && !result ? 'border-slate-900 bg-slate-50' : ''">
          <input
            v-model="chosen"
            type="radio"
            :value="opt.id"
            :disabled="!!result"
            name="option"
            class="mt-1"
          />
          <span class="text-sm"><strong>{{ opt.letter }}.</strong> {{ opt.content }}</span>
        </label>
        <button type="submit" :disabled="!!result || submitting" class="w-full rounded-full bg-slate-900 px-4 py-2.5 font-semibold text-white hover:bg-slate-700 disabled:opacity-50">Submit</button>
      </form>

      <div v-if="result" class="mt-4 rounded-2xl p-4" :class="result.correct ? 'bg-emerald-50' : 'bg-red-50'">
        <p class="font-semibold" :class="result.correct ? 'text-emerald-700' : 'text-red-700'">
          {{ result.correct ? 'Correct' : 'Wrong — and that tells us something.' }}
        </p>
        <p v-if="result.explanation" class="mt-1 text-sm text-slate-700">{{ result.explanation }}</p>
        <p v-if="result.misconception" class="mt-1 text-sm text-amber-800">Trap to watch: {{ result.misconception }}</p>
        <p v-if="result.retry_queued" class="mt-1 text-sm font-medium text-slate-700">Queued: a retest on this trap is coming up.</p>
        <ul class="mt-2 space-y-1 text-sm text-slate-600">
          <template v-for="o in resultOptions" :key="o.id">
            <li v-if="o.explanation">
              <strong>{{ o.letter }}.</strong> {{ o.explanation }}
            </li>
          </template>
        </ul>
        <p v-if="correctLetter" class="mt-2 text-sm text-slate-600">Correct answer: <strong>{{ correctLetter }}</strong></p>
        <div class="mt-3 rounded-2xl border border-slate-200 bg-white p-3">
          <button @click="showExplain = !showExplain" class="text-sm font-semibold text-slate-900 hover:underline">
            {{ showExplain ? 'Hide the challenge −' : 'Explain it back for +XP — can you teach this?' }}
          </button>
          <div v-if="showExplain" class="mt-2">
            <textarea v-model="explainText" rows="3" maxlength="2000" placeholder="Explain the idea in your own words (min 40 characters)…" class="w-full rounded-2xl border border-slate-200 p-3 text-sm focus:border-slate-400 focus:outline-none"></textarea>
            <div class="mt-2 flex gap-2">
              <button @click="submitExplain" :disabled="explaining || !explainText.trim()" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50">
                {{ explaining ? 'Grading…' : 'Submit explanation' }}
              </button>
              <button v-if="voiceSupported && examVoice" @click="dictate" :disabled="transcribingVoice" class="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500 disabled:opacity-50">
                {{ listeningVoice ? '⏹ Stop & transcribe' : transcribingVoice ? 'Transcribing…' : '🎙 Dictate' }}
              </button>
              <button v-else-if="voiceSupported" disabled title="Voice input unlocks on listening/speaking exams (e.g. SAT Reading & Writing)" class="cursor-not-allowed rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-400">
                🎙 Dictate
              </button>
            </div>
            <div v-if="explainResult" class="mt-2 rounded-2xl p-3 text-sm" :class="explainResult.graded ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'">
              <p v-if="explainResult.graded" class="font-semibold">Score {{ explainResult.score_10 }}/10 · +{{ explainResult.xp_awarded }} XP</p>
              <p v-if="explainResult.graded && explainResult.capped" class="text-xs">Daily explain bonus reached — grade kept, no XP this time.</p>
              <p v-if="explainResult.graded && explainResult.feedback" class="mt-1">{{ explainResult.feedback }}</p>
              <p v-if="!explainResult.graded">{{ explainResult.note || 'Grading failed — try again.' }}</p>
            </div>
          </div>
        </div>
        <button @click="next" class="mt-3 w-full rounded-full bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Next question →</button>
      </div>
    </div>
  </div>
</template>
