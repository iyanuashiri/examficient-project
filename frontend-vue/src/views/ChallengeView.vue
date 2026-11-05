<script>
import { apiFetch } from '@/api/client.js'
import { VOICE_SUPPORTED, startRecording } from '@/api/voice.js'

export default {
  data() {
    return {
      exam: null,
      board: null,
      past: [],
      forms: {},
      listening: {},
      recorders: {},
      voiceSupported: VOICE_SUPPORTED,
      loading: true,
      error: '',
    }
  },
  computed: {
    id() {
      return this.$route.params.id
    },
  },
  async created() {
    try {
      const [mine, board, past] = await Promise.all([
        apiFetch('/exams/mine/'),
        apiFetch(`/practice/challenges/?exam_id=${this.id}`),
        apiFetch(`/practice/explain/history/?exam_id=${this.id}&limit=20`),
      ])
      this.exam = mine.find((e) => String(e.id) === String(this.id)) || null
      this.board = board
      this.past = past
    } catch (e) {
      this.error = e.message
      if (e.status === 401) this.$router.push('/login')
    } finally {
      this.loading = false
    }
  },
  methods: {
    formFor(qid) {
      if (!this.forms[qid]) this.forms[qid] = { text: '', result: null, busy: false }
      return this.forms[qid]
    },
    async submit(qid) {
      const f = this.formFor(qid)
      if (!f.text.trim() || f.busy) return
      f.busy = true
      this.error = ''
      try {
        f.result = await apiFetch('/practice/explain/', {
          method: 'POST',
          body: { question_id: qid, text: f.text.trim() },
        })
        this.past = await apiFetch(`/practice/explain/history/?exam_id=${this.id}&limit=20`)
        if (this.board) {
          this.board = await apiFetch(`/practice/challenges/?exam_id=${this.id}`)
        }
      } catch (e) {
        this.error = e.message
      } finally {
        f.busy = false
      }
    },
    dictate(qid) {
      // Voice input via Meta Muse Voice Transcribe: record WAV in-browser,
      // POST to /practice/transcribe/, transcript lands in the same textarea
      // and travels the identical grading path as typed text.
      if (this.listening[qid] === true) {
        // Second press: stop, transcribe, fill.
        const rec = this.recorders[qid]
        this.listening[qid] = 'transcribing'
        this.error = ''
        rec.stop().then(async (wav) => {
          try {
            const fd = new FormData()
            fd.append('file', wav, 'audio.wav')
            const r = await apiFetch('/practice/transcribe/', { method: 'POST', body: fd, raw: true, timeoutMs: 90000 })
            const f = this.formFor(qid)
            f.text = (f.text ? f.text + ' ' : '') + r.transcript
          } catch (e) {
            this.error = e.message
          } finally {
            this.listening[qid] = false
          }
        })
        return
      }
      if (this.listening[qid]) return
      startRecording().then((rec) => {
        this.recorders[qid] = rec
        this.listening[qid] = true
      }).catch((e) => {
        this.error = e.message || 'Microphone unavailable.'
      })
    },
  },
}
</script>

<template>
  <div>
    <router-link to="/challenges" class="text-sm text-slate-500 hover:text-slate-900">← Challenges</router-link>
    <h2 class="mt-2 font-display text-2xl font-bold tracking-tight">{{ exam ? exam.name : 'Challenge' }}</h2>
    <p class="mt-1 text-sm text-slate-500">Explain the idea underneath each question — in words or out loud. The AI grades depth.</p>
    <p v-if="loading" class="mt-4 text-slate-500">Loading…</p>
    <p v-if="error" class="mb-3 rounded-2xl bg-red-50 p-3 text-sm text-red-700">{{ error }}</p>

    <template v-if="!loading && board">
      <p class="mt-6 text-xs font-semibold tracking-widest text-slate-400">TODAY'S CHALLENGES</p>
      <div v-if="board.daily.length" class="mt-2 space-y-3">
        <div v-for="ch in board.daily" :key="'d' + ch.question_id" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-xs font-semibold text-slate-400">DAILY · <span v-if="ch.done" class="text-emerald-600">DONE{{ ch.best_score != null ? ` · BEST ${ch.best_score}/10` : '' }}</span><span v-else class="text-slate-500">NOT DONE</span></p>
          <p class="mt-1 text-sm font-medium">{{ ch.stem }}</p>
          <div class="mt-2">
            <textarea v-model="formFor(ch.question_id).text" rows="2" maxlength="2000" placeholder="Explain the concept in your own words (min 40 characters)…" class="w-full rounded-2xl border border-slate-200 p-3 text-sm focus:border-slate-400 focus:outline-none"></textarea>
            <div class="mt-2 flex gap-2">
              <button @click="submit(ch.question_id)" :disabled="formFor(ch.question_id).busy || !formFor(ch.question_id).text.trim()" class="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50">
                {{ formFor(ch.question_id).busy ? 'Grading…' : 'Submit explanation' }}
              </button>
              <button v-if="voiceSupported && exam && exam.voice_enabled" @click="dictate(ch.question_id)" class="rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500" :title="'Dictate instead of typing'">
                {{ listening[ch.question_id] === true ? '⏹ Stop & transcribe' : listening[ch.question_id] ? 'Transcribing…' : '🎙 Dictate' }}
              </button>
              <button v-else-if="voiceSupported" disabled title="Voice input unlocks on listening/speaking exams (e.g. SAT Reading & Writing)" class="cursor-not-allowed rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-400">
                🎙 Dictate
              </button>
            </div>
            <div v-if="formFor(ch.question_id).result" class="mt-2 rounded-2xl p-3 text-sm" :class="formFor(ch.question_id).result.graded ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'">
              <template v-if="formFor(ch.question_id).result.graded">
                <p class="font-semibold">Score {{ formFor(ch.question_id).result.score_10 }}/10 · +{{ formFor(ch.question_id).result.xp_awarded }} XP</p>
                <p v-if="formFor(ch.question_id).result.feedback" class="mt-1">{{ formFor(ch.question_id).result.feedback }}</p>
              </template>
              <p v-else>{{ formFor(ch.question_id).result.note || 'Grading failed — try again.' }}</p>
            </div>
          </div>
        </div>
      </div>
      <p v-else class="mt-2 text-sm text-slate-500">Nothing today — answer questions to unlock tomorrow's set. <router-link :to="`/practice/${id}`" class="font-semibold text-slate-900 hover:underline">Practice now →</router-link></p>

      <p class="mt-6 text-xs font-semibold tracking-widest text-slate-400">WEEKLY SHOWDOWN{{ board.weekly_unlocked ? '' : ` · UNLOCKS ${board.unlocks_at}` }}</p>
      <div v-if="board.weekly_unlocked && board.weekly.length" class="mt-2 space-y-3">
        <div v-for="ch in board.weekly" :key="'w' + ch.question_id" class="rounded-3xl border-2 border-slate-900 bg-white p-5 shadow-sm">
          <p class="text-xs font-semibold text-slate-400">WEEKLY · <span v-if="ch.done" class="text-emerald-600">DONE{{ ch.best_score != null ? ` · BEST ${ch.best_score}/10` : '' }}</span><span v-else class="text-slate-500">NOT DONE</span></p>
          <p class="mt-1 text-sm font-medium">{{ ch.stem }}</p>
          <div class="mt-2">
            <textarea v-model="formFor(ch.question_id).text" rows="2" maxlength="2000" placeholder="Explain the concept in your own words (min 40 characters)…" class="w-full rounded-2xl border border-slate-200 p-3 text-sm focus:border-slate-400 focus:outline-none"></textarea>
            <div class="mt-2 flex gap-2">
              <button @click="submit(ch.question_id)" :disabled="formFor(ch.question_id).busy || !formFor(ch.question_id).text.trim()" class="mt-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50">
                {{ formFor(ch.question_id).busy ? 'Grading…' : 'Submit explanation' }}
              </button>
              <button v-if="voiceSupported && exam && exam.voice_enabled" @click="dictate(ch.question_id)" class="mt-2 rounded-full border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500">
                {{ listening[ch.question_id] === true ? '⏹ Stop & transcribe' : listening[ch.question_id] ? 'Transcribing…' : '🎙 Dictate' }}
              </button>
              <button v-else-if="voiceSupported" disabled title="Voice input unlocks on listening/speaking exams (e.g. SAT Reading & Writing)" class="mt-2 cursor-not-allowed rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-400">
                🎙 Dictate
              </button>
            </div>
            <div v-if="formFor(ch.question_id).result" class="mt-2 rounded-2xl p-3 text-sm" :class="formFor(ch.question_id).result.graded ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'">
              <template v-if="formFor(ch.question_id).result.graded">
                <p class="font-semibold">Score {{ formFor(ch.question_id).result.score_10 }}/10 · +{{ formFor(ch.question_id).result.xp_awarded }} XP</p>
                <p v-if="formFor(ch.question_id).result.feedback" class="mt-1">{{ formFor(ch.question_id).result.feedback }}</p>
              </template>
              <p v-else>{{ formFor(ch.question_id).result.note || 'Grading failed — try again.' }}</p>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="!board.weekly_unlocked" class="mt-2 space-y-2">
        <div v-for="i in 5" :key="i" class="rounded-3xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
          🔒 Weekly challenge {{ i }} — your 5 hardest questions of the week, revealed {{ board.unlocks_at }}.
        </div>
      </div>
      <p v-else class="mt-2 text-sm text-slate-500">No weekly set — answer questions this week to build one.</p>

      <div v-if="past.length" class="mt-6">
        <p class="text-xs font-semibold tracking-widest text-slate-400">YOUR EXPLANATIONS</p>
        <ul class="mt-2 space-y-2">
          <li v-for="p in past" :key="p.id" class="rounded-3xl border border-slate-200 bg-white p-4 text-sm shadow-sm">
            <p class="font-medium">{{ p.stem }}</p>
            <p class="mt-1 text-slate-500">{{ p.feedback || 'Ungraded' }} · <span class="font-semibold text-slate-700">{{ p.score_10 }}/10 · +{{ p.xp }} XP</span></p>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
