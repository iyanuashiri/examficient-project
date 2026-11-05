<script>
import { getToken } from '@/api/client.js'

const DEMO_QUESTIONS = [
  {
    topic: 'Cell Biology',
    stem: 'Which organelle is the site of photosynthesis?',
    options: [
      { id: 'a', label: 'A', content: 'Mitochondrion', trap: 'You confused the two energy organelles — mitochondria release energy, chloroplasts capture it.' },
      { id: 'b', label: 'B', content: 'Chloroplast', trap: null },
      { id: 'c', label: 'C', content: 'Nucleus', trap: 'The nucleus holds DNA, but it captures no light energy.' },
      { id: 'd', label: 'D', content: 'Ribosome', trap: 'Ribosomes build proteins — nothing to do with light.' },
    ],
    correctId: 'b',
    explanation: 'Chlorophyll inside chloroplasts traps light energy to power glucose synthesis.',
  },
  {
    topic: 'Transport in Humans',
    stem: 'Which component of blood carries oxygen?',
    options: [
      { id: 'a', label: 'A', content: 'White blood cells', trap: 'White cells fight infection — they carry no oxygen.' },
      { id: 'b', label: 'B', content: 'Plasma', trap: 'Plasma is the fluid, not a cell — it transports, but haemoglobin does the carrying.' },
      { id: 'c', label: 'C', content: 'Red blood cells', trap: null },
      { id: 'd', label: 'D', content: 'Platelets', trap: 'Platelets clot blood — they carry no oxygen.' },
    ],
    correctId: 'c',
    explanation: 'Haemoglobin in red blood cells binds oxygen in the lungs and releases it in tissues.',
  },
  {
    topic: 'Genetics',
    stem: 'The classic 3:1 phenotypic ratio appears in…',
    options: [
      { id: 'a', label: 'A', content: 'A test cross', trap: 'A test cross gives 1:1. The 3:1 shows up one generation later.' },
      { id: 'b', label: 'B', content: 'The F2 of a monohybrid cross', trap: null },
      { id: 'c', label: 'C', content: 'A dihybrid cross, always', trap: 'Dihybrid gives 9:3:3:1 — you mixed up your ratios.' },
      { id: 'd', label: 'D', content: 'Incomplete dominance', trap: 'Incomplete dominance gives 1:2:1. Close — but not 3:1.' },
    ],
    correctId: 'b',
    explanation: 'Selfing two F1 heterozygotes (Aa × Aa) yields 3 dominant : 1 recessive in the F2.',
  },
]

const MAP_TOPICS = [
  { name: 'Cell Biology', pct: 82, note: 'Exam-ready' },
  { name: 'Transport in Humans', pct: 64, note: 'On track' },
  { name: 'Genetics', pct: 35, note: 'Needs work · 45 min to +12%' },
  { name: 'Ecology', pct: 71, note: 'On track' },
  { name: 'Reproduction', pct: 22, note: 'Needs work · 30 min to +9%' },
]

export default {
  data() {
    return {
      picked: 'SAT Math',
      exams: ['SAT Math', 'GRE Quant', 'A-Levels Biology', 'JAMB Biology', 'AWS SAA-C03'],
      demoIndex: 0,
      demoPicked: null,
      demoAnswered: false,
      demoScore: 0,
      demoDone: false,
    demoShown: [],
      mapShown: false,
      dialShown: false,
      faqs: [
        {
          q: 'Is this just past questions?',
          a: 'Past questions are the seed. The engine decides the order, the difficulty, and when to re-test you — and tracks what each miss reveals about your understanding.',
        },
        {
          q: 'How is this different from asking ChatGPT?',
          a: 'ChatGPT explains brilliantly and forgets everything. Examficient keeps a live map of what you know per topic, calibrates difficulty to real exam weights, and never lets a weak spot slip through.',
        },
        {
          q: 'What about theory / essay exams?',
          a: 'Objective drills come first — plus explain-it-back challenges, where you write or speak the concept and AI grades your depth. Full essay grading is on the roadmap.',
        },
        {
          q: 'Can I speak my answers instead of typing?',
          a: 'On listening/speaking exams like SAT Reading & Writing, yes — the mic transcribes you and grading works exactly like text. Written exams (JAMB, WAEC) keep voice off by design.',
        },
        {
          q: 'Can I upload my own syllabus?',
          a: 'Yes. Private uploads run on the same adaptive engine as featured exams — your content stays yours.',
        },
      ],
    }
  },
  computed: {
    demoQ() {
      return DEMO_QUESTIONS[this.demoIndex]
    },
    demoPickedOption() {
      return this.demoQ.options.find((o) => o.id === this.demoPicked) || null
    },
    demoPct() {
      return Math.round((this.demoScore / DEMO_QUESTIONS.length) * 100)
    },
  },
  mounted() {
    const els = this.$el.querySelectorAll('.reveal')
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.15 },
    )
    els.forEach((el) => io.observe(el))
    const watch = (id, key) => {
      const el = this.$el.querySelector(id)
      if (!el) return
      const o = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            this[key] = true
            o.disconnect()
          }
        },
        { threshold: 0.4 },
      )
      o.observe(el)
    }
    watch('#readiness-dial', 'dialShown')
    watch('#knowledge-map', 'mapShown')
  },
  created() {
    this.shuffleDemo()
  },
  methods: {
    shuffleDemo() {
      // Letters are presentation: shuffle per question, assign at render.
      const arr = this.demoQ.options.map((o) => ({ ...o }))
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[arr[i], arr[j]] = [arr[j], arr[i]]
      }
      this.demoShown = arr.map((o, i) => ({ ...o, letter: 'ABCD'[i] || `O${i + 1}` }))
      this.demoPicked = null
      this.demoAnswered = false
    },
    getStarted() {
      this.$router.push(getToken() ? '/exams' : '/register')
    },
    pickDemo(id) {
      if (this.demoAnswered) return
      this.demoPicked = id
    },
    submitDemo() {
      if (!this.demoPicked || this.demoAnswered) return
      this.demoAnswered = true
      if (this.demoPicked === this.demoQ.correctId) this.demoScore += 1
    },
    nextDemo() {
      if (this.demoIndex + 1 >= DEMO_QUESTIONS.length) {
        this.demoDone = true
        return
      }
      this.demoIndex += 1
      this.shuffleDemo()
    },
    resetDemo() {
      this.demoIndex = 0
      this.demoScore = 0
      this.demoDone = false
      this.shuffleDemo()
    },
  },
}
</script>

<template>
  <div class="bg-white font-sans text-slate-900 antialiased">
    <!-- HERO -->
    <section class="mx-auto max-w-6xl px-4 pb-14 pt-14 text-center sm:pt-20">
      <p class="reveal mx-auto mb-5 inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-1.5 text-xs font-semibold tracking-wide text-slate-600">
        <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
        SAT · GRE · A-LEVELS · JAMB · AWS · CFA
      </p>
      <h1 class="reveal mx-auto max-w-4xl font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl">
        Read less. Know more.<br />Pass exams.
      </h1>
      <p class="reveal mx-auto mt-6 max-w-2xl text-lg text-slate-500 sm:text-xl">
        Examficient's adaptive engine drills you with exam-style multiple-choice questions, learns
        exactly what you know — and tells you when you're ready to sit.
      </p>
      <div class="reveal mx-auto mt-8 flex max-w-xl flex-col items-center justify-center gap-3 sm:flex-row">
        <select v-model="picked" aria-label="Pick an exam" class="w-full rounded-full border border-slate-300 bg-white px-5 py-3.5 text-base sm:flex-1">
          <option v-for="e in exams" :key="e">{{ e }}</option>
        </select>
        <button @click="getStarted" class="w-full rounded-full bg-slate-900 px-8 py-3.5 text-base font-semibold text-white transition hover:bg-slate-700 sm:w-auto">
          Practice {{ picked }} free
        </button>
      </div>

      <!-- PRODUCT MOCK -->
      <div class="reveal relative mx-auto mt-14 max-w-4xl">
        <div class="grid gap-4 text-left md:grid-cols-5">
          <div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 md:col-span-3">
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold text-slate-400">EXAM READINESS</p>
              <span class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">+6% this week</span>
            </div>
            <p class="mt-2 font-display text-6xl font-bold">87<span class="text-2xl text-slate-400">%</span></p>
            <p class="mt-1 text-sm text-slate-500">SAT Math · target 1450</p>
            <div class="mt-4 space-y-3">
              <div v-for="t in [{ n: 'Heart of Algebra', p: 82 }, { n: 'Problem Solving', p: 71 }, { n: 'Passport to Adv. Math', p: 35 }]" :key="t.n">
                <div class="mb-1 flex justify-between text-xs"><span class="font-medium">{{ t.n }}</span><span class="text-slate-400">{{ t.p }}%</span></div>
                <div class="h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full" :class="t.p < 50 ? 'bg-amber-400' : 'bg-emerald-500'" :style="{ width: `${t.p}%` }"></div></div>
              </div>
            </div>
          </div>
          <div class="flex flex-col gap-4 md:col-span-2">
            <div class="animate-float rounded-3xl border border-slate-200 bg-white p-5 shadow-xl shadow-slate-200/60">
              <p class="text-xs font-semibold text-slate-400">NOW DRILLING · PASSPORT TO ADV. MATH</p>
              <p class="mt-2 text-sm font-medium">If (x − 2)(x − 3) = 0, then x =</p>
              <div class="mt-3 space-y-2 text-sm">
                <div class="rounded-xl border border-slate-200 px-3 py-2">A. 2 or 3</div>
                <div class="rounded-xl border border-red-200 bg-red-50 px-3 py-2">B. −2 or −3 <span class="text-red-500">— trapped</span></div>
              </div>
              <p class="mt-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">Sign flip: x − 2 = 0 means x = +2, not −2.</p>
            </div>
            <div class="animate-float-slow rounded-3xl bg-slate-900 p-5 text-white shadow-xl">
              <p class="text-xs font-semibold text-slate-400">DIAGNOSIS</p>
              <p class="mt-1 text-sm">"You keep flipping signs when solving factors. 3 questions, same mistake."</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- EXAM LANES -->
    <div class="space-y-3 overflow-hidden border-y border-slate-100 bg-slate-50/60 py-4">
      <div v-for="lane in [
        { label: 'HIGH SCHOOL', items: ['SAT', 'ACT', 'GCSE', 'A-LEVELS', 'AP', 'WAEC', 'JAMB'], reverse: false },
        { label: 'GRAD SCHOOL', items: ['GRE', 'GMAT', 'MCAT', 'LSAT'], reverse: true },
        { label: 'PROFESSIONAL', items: ['AWS', 'PMP', 'CFA', 'CPA', 'META CERTIFIED'], reverse: false },
      ]" :key="lane.label" class="mx-auto flex max-w-6xl items-center gap-4 px-4">
        <span class="w-28 shrink-0 text-right text-[11px] font-bold tracking-widest text-slate-400">{{ lane.label }}</span>
        <div class="flex-1 overflow-hidden">
          <div class="flex w-max gap-10 whitespace-nowrap text-sm font-semibold tracking-wide text-slate-500" :class="lane.reverse ? 'animate-marquee-reverse' : 'animate-marquee'">
            <span v-for="n in 2" :key="n" class="flex gap-10">
              <span v-for="e in lane.items" :key="e">{{ e }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- INTERACTIVE DEMO -->
    <section id="demo" class="mx-auto max-w-3xl scroll-mt-20 px-4 py-20">
      <p class="reveal text-sm font-semibold tracking-widest text-slate-400">LIVE DEMO — NO SIGN-UP</p>
      <h2 class="reveal mt-2 font-display text-3xl font-bold tracking-tight sm:text-5xl">Feel the engine in 60 seconds.</h2>
      <p class="reveal mt-3 text-lg text-slate-500">Three real exam-style questions. Miss one on purpose — the diagnosis is the product.</p>

      <div class="reveal mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 sm:p-8">
        <div v-if="!demoDone">
          <div class="mb-4 flex items-center justify-between text-xs text-slate-400">
            <span class="rounded-full bg-slate-100 px-3 py-1 font-semibold">{{ demoQ.topic }}</span>
            <span>Question {{ demoIndex + 1 }} of 3</span>
          </div>
          <div class="mb-4 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div class="h-full rounded-full bg-slate-900 transition-all" :style="{ width: `${(demoIndex / 3) * 100}%` }"></div>
          </div>
          <p class="mb-4 text-lg font-medium">{{ demoQ.stem }}</p>
          <div class="space-y-2">
            <button
              v-for="opt in demoShown"
              :key="opt.id"
              @click="pickDemo(opt.id)"
              :disabled="demoAnswered"
              class="flex w-full items-start gap-3 rounded-2xl border p-3 text-left text-sm transition"
              :class="[
                demoAnswered && opt.id === demoQ.correctId ? 'border-emerald-400 bg-emerald-50' : '',
                demoAnswered && opt.id === demoPicked && opt.id !== demoQ.correctId ? 'border-red-300 bg-red-50' : '',
                !demoAnswered && demoPicked === opt.id ? 'border-slate-900 bg-slate-50' : '',
                !demoAnswered && demoPicked !== opt.id ? 'border-slate-200 hover:border-slate-400' : '',
              ]"
            >
              <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-slate-300 text-xs font-bold">{{ opt.letter }}</span>
              <span>{{ opt.content }}</span>
            </button>
          </div>

          <div v-if="demoAnswered" class="mt-4 rounded-2xl bg-slate-50 p-4 text-sm">
            <p class="font-semibold" :class="demoPicked === demoQ.correctId ? 'text-emerald-700' : 'text-red-600'">
              {{ demoPicked === demoQ.correctId ? 'Correct.' : 'Wrong — and that tells us something.' }}
            </p>
            <p class="mt-1 text-slate-600">{{ demoQ.explanation }}</p>
            <p v-if="demoPickedOption && demoPickedOption.trap" class="mt-2 text-amber-700">Trap to watch: {{ demoPickedOption.trap }}</p>
          </div>

          <div class="mt-4 flex gap-3">
            <button v-if="!demoAnswered" @click="submitDemo" :disabled="!demoPicked" class="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-40">Submit</button>
            <button v-else @click="nextDemo" class="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">
              {{ demoIndex + 1 >= 3 ? 'See my readiness' : 'Next question →' }}
            </button>
          </div>
        </div>

        <div v-else class="text-center">
          <p class="text-sm font-semibold text-slate-400">YOUR MINI READINESS</p>
          <p class="mt-1 font-display text-6xl font-bold" :class="demoPct >= 67 ? 'text-emerald-600' : 'text-amber-500'">{{ demoPct }}%</p>
          <p class="mx-auto mt-3 max-w-md text-sm text-slate-500">
            {{ demoPct === 100 ? 'Flawless. The real engine would now push you to harder, higher-weight topics.' : 'Imagine this across your whole syllabus — updated with every answer, weighted by real exam marks.' }}
          </p>
          <div class="mt-5 flex justify-center gap-3">
            <button @click="getStarted" class="rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Build my full profile</button>
            <button @click="resetDemo" class="rounded-full border border-slate-300 px-6 py-2.5 text-sm font-semibold hover:bg-slate-50">Retry demo</button>
          </div>
        </div>
      </div>
    </section>

    <!-- KNOWLEDGE MAP -->
    <section id="knowledge-map" class="border-y border-slate-100 bg-slate-50/60">
      <div class="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 md:grid-cols-2">
        <div>
          <p class="reveal text-sm font-semibold tracking-widest text-slate-400">YOUR KNOWLEDGE MAP</p>
          <h2 class="reveal mt-2 font-display text-3xl font-bold tracking-tight sm:text-5xl">Know exactly what you know.</h2>
          <p class="reveal mt-4 text-lg text-slate-500">
            Every answer redraws your map — topic by topic, misconception by
            misconception. No more re-reading chapters you've already mastered.
          </p>
          <div class="reveal mt-6 grid grid-cols-3 gap-4 text-center">
            <div class="rounded-2xl border border-slate-200 bg-white p-4"><p class="font-display text-2xl font-bold">248</p><p class="text-xs text-slate-500">questions answered</p></div>
            <div class="rounded-2xl border border-slate-200 bg-white p-4"><p class="font-display text-2xl font-bold">71%</p><p class="text-xs text-slate-500">accuracy · +9 this week</p></div>
            <div class="rounded-2xl border border-slate-200 bg-white p-4"><p class="font-display text-2xl font-bold">~6d</p><p class="text-xs text-slate-500">to exam-ready</p></div>
          </div>
        </div>
        <div class="reveal rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50">
          <p class="text-sm font-semibold text-slate-400">SAT MATH · 14 SKILLS MAPPED</p>
          <div class="mt-4 space-y-4">
            <div v-for="t in [
              { name: 'Passport to Adv. Math', pct: 35, note: 'Needs work · 45 min to +12%' },
              { name: 'Geometry & Trig', pct: 58, note: 'Climbing · +9 this week' },
              { name: 'Problem Solving', pct: 71, note: 'On track' },
              { name: 'Heart of Algebra', pct: 82, note: 'Exam-ready' },
            ]" :key="t.name">
              <div class="mb-1 flex items-baseline justify-between text-sm">
                <span class="font-medium">{{ t.name }}</span>
                <span class="text-xs text-slate-400">{{ t.note }}</span>
              </div>
              <div class="h-2.5 overflow-hidden rounded-full bg-slate-100">
                <div
                  class="h-full rounded-full transition-all duration-1000"
                  :class="t.pct < 50 ? 'bg-amber-400' : 'bg-emerald-500'"
                  :style="{ width: mapShown ? `${t.pct}%` : '0%' }"
                ></div>
              </div>
            </div>
          </div>
          <p class="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">The engine serves Passport to Adv. Math next — highest points per minute of study.</p>
        </div>
      </div>
    </section>

    <!-- CHALLENGES -->
    <section class="mx-auto max-w-6xl px-4 py-20">
      <p class="reveal text-sm font-semibold tracking-widest text-slate-400">EXPLAIN IT BACK</p>
      <h2 class="reveal mt-2 max-w-2xl font-display text-3xl font-bold tracking-tight sm:text-5xl">Knowing the answer isn't the same as knowing it.</h2>
      <p class="reveal mt-4 max-w-2xl text-lg text-slate-500">
        Challenges ask you to teach the concept back — in writing or out loud.
        Meta AI grades your depth, XP scales, and your leaderboard rank moves.
      </p>
      <div class="mt-8 grid gap-4 md:grid-cols-3">
        <div class="reveal rounded-3xl border border-slate-200 bg-white p-6">
          <p class="text-xs font-semibold tracking-widest text-slate-400">TODAY'S CHALLENGES · 3</p>
          <p class="mt-2 font-semibold">Fresh every morning</p>
          <p class="mt-1 text-sm text-slate-500">Engine-picked from your weakest topics. Same set for everyone — did you do today's?</p>
          <div class="mt-4 space-y-2 text-sm">
            <div class="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800">Photosynthesis… <span class="font-semibold">8/10 · +8 XP</span></div>
            <div class="rounded-xl bg-slate-50 px-3 py-2 text-slate-600">Monohybrid cross… <span class="font-semibold">not done</span></div>
          </div>
        </div>
        <div class="reveal rounded-3xl bg-slate-900 p-6 text-white shadow-xl">
          <p class="text-xs font-semibold tracking-widest text-slate-400">WEEKLY SHOWDOWN · 5</p>
          <p class="mt-2 font-semibold">Your 5 hardest questions, revealed Sunday</p>
          <p class="mt-1 text-sm text-slate-400">Locked all week with a countdown. The week's boss fight.</p>
          <div class="mt-4 space-y-2 text-sm">
            <div class="rounded-xl bg-white/10 px-3 py-2">🔒 Weekly challenge 1 — revealed Sunday</div>
            <div class="rounded-xl bg-white/10 px-3 py-2">🔒 Weekly challenge 2 — revealed Sunday</div>
          </div>
        </div>
        <div class="reveal rounded-3xl border border-slate-200 bg-white p-6">
          <p class="text-xs font-semibold tracking-widest text-slate-400">VOICE, WHERE IT COUNTS</p>
          <p class="mt-2 font-semibold">Say it, don't type it</p>
          <p class="mt-1 text-sm text-slate-500">On listening/speaking exams the mic transcribes you and grading works exactly like text.</p>
          <div class="mt-4 flex items-center gap-2 text-sm">
            <span class="rounded-full bg-slate-900 px-4 py-2 font-semibold text-white">🎙 Dictate</span>
            <span class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">SAT Reading & Writing</span>
          </div>
          <p class="mt-3 text-xs text-slate-400">Written exams (JAMB, WAEC) keep voice off by design.</p>
        </div>
      </div>
    </section>

    <!-- COMPARISON -->
    <section class="mx-auto max-w-6xl px-4 py-20">
      <p class="reveal text-sm font-semibold tracking-widest text-slate-400">WHY NOT JUST CHATGPT?</p>
      <h2 class="reveal mt-2 max-w-2xl font-display text-3xl font-bold tracking-tight sm:text-5xl">ChatGPT explains. Examficient remembers.</h2>
      <div class="mt-8 grid gap-4 md:grid-cols-3">
        <div class="reveal rounded-3xl border border-slate-200 bg-white p-6">
          <p class="font-display text-lg font-bold text-slate-400">Raw LLM chat</p>
          <ul class="mt-3 space-y-2 text-sm text-slate-500">
            <li>✕ Forgets what you missed yesterday</li>
            <li>✕ Random difficulty, no exam weights</li>
            <li>✕ "Wrong, it's C" — no diagnosis</li>
            <li>✕ No idea when you're ready</li>
          </ul>
        </div>
        <div class="reveal rounded-3xl border border-slate-200 bg-white p-6">
          <p class="font-display text-lg font-bold text-slate-400">Video courses & textbooks</p>
          <ul class="mt-3 space-y-2 text-sm text-slate-500">
            <li>✕ Same lesson for everyone</li>
            <li>✕ Hours of re-watching what you know</li>
            <li>✕ Static pages, zero feedback loop</li>
            <li>✕ Out-competed by AI on explanations</li>
          </ul>
        </div>
        <div class="reveal rounded-3xl bg-slate-900 p-6 text-white shadow-xl">
          <p class="font-display text-lg font-bold">Examficient</p>
          <ul class="mt-3 space-y-2 text-sm text-slate-300">
            <li>✓ A live map of what you know, per topic</li>
            <li>✓ An adaptive engine serving questions at your edge</li>
            <li>✓ Every distractor mapped to a misconception</li>
            <li>✓ Explain-it-back challenges graded by AI</li>
            <li>✓ A predicted score that says when to book</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- HOW IT WORKS -->
    <section class="border-y border-slate-100 bg-slate-50/60">
      <div class="mx-auto max-w-6xl px-4 py-20">
        <p class="reveal text-sm font-semibold tracking-widest text-slate-400">HOW IT WORKS</p>
        <h2 class="reveal mt-2 font-display text-3xl font-bold tracking-tight sm:text-5xl">From syllabus to certainty.</h2>
        <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div v-for="(s, i) in [
            { t: 'Pick or upload', d: 'Choose a featured exam — SAT, GRE, A-Levels, JAMB — or upload your own syllabus.' },
            { t: 'Get probed', d: 'A short calibration set maps your level across every topic in minutes.' },
            { t: 'Drill the edge', d: 'The adaptive engine holds every question where your pass chance is ~70%: never boring, never crushing.' },
            { t: 'Prove readiness', d: 'Your predicted score climbs as weak topics clear. Book when it says so.' },
          ]" :key="s.t" class="reveal rounded-3xl border border-slate-200 bg-white p-6">
            <p class="font-display text-4xl font-bold text-slate-200">0{{ i + 1 }}</p>
            <p class="mt-2 font-semibold">{{ s.t }}</p>
            <p class="mt-1 text-sm text-slate-500">{{ s.d }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- READINESS -->
    <section id="readiness-dial" class="mx-auto max-w-6xl px-4 py-20 text-center">
      <p class="reveal text-sm font-semibold tracking-widest text-slate-400">EXAM READINESS</p>
      <h2 class="reveal mx-auto mt-2 max-w-2xl font-display text-3xl font-bold tracking-tight sm:text-5xl">One number. Zero guessing.</h2>
      <div class="reveal mx-auto mt-8 w-fit">
        <svg width="220" height="220" viewBox="0 0 140 140">
          <circle cx="70" cy="70" r="54" fill="none" stroke="#f1f5f9" stroke-width="12" />
          <circle
            cx="70" cy="70" r="54" fill="none" stroke="#10b981" stroke-width="12" stroke-linecap="round"
            :stroke-dasharray="339.29" :stroke-dashoffset="dialShown ? 339.29 * (1 - 0.87) : 339.29"
            transform="rotate(-90 70 70)" style="transition: stroke-dashoffset 1.6s ease-out"
          />
          <text x="70" y="68" text-anchor="middle" fill="#0f172a" font-size="26" font-weight="700">87%</text>
          <text x="70" y="88" text-anchor="middle" fill="#94a3b8" font-size="10">PREDICTED</text>
        </svg>
      </div>
      <p class="reveal mx-auto mt-6 max-w-xl text-lg text-slate-500">"If you sat SAT Math today: <strong class="text-slate-900">87% — on pace for 1450+.</strong> Spend 45 minutes on Passport to Advanced Math to lock in 1500."</p>
      <button @click="getStarted" class="reveal mt-6 rounded-full bg-slate-900 px-8 py-3.5 font-semibold text-white hover:bg-slate-700">Get my number</button>
    </section>

    <!-- EXAMS + PRICING -->
    <section class="border-t border-slate-100">
      <div class="mx-auto max-w-6xl px-4 py-20">
        <p class="reveal text-sm font-semibold tracking-widest text-slate-400">COVERAGE</p>
        <h2 class="reveal mt-2 font-display text-3xl font-bold tracking-tight sm:text-5xl">Nigeria, US, UK, and beyond.</h2>
        <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div v-for="e in [
            { n: 'SAT', d: 'Objective drills · readiness tracking · 🎙 voice' },
            { n: 'GRE', d: 'Objective drills · readiness tracking' },
            { n: 'A-Levels', d: 'Objective drills · readiness tracking' },
            { n: 'JAMB', d: 'Objective drills · readiness tracking' },
            { n: 'AWS', d: 'Objective drills · readiness tracking' },
            { n: 'CFA', d: 'Objective drills · readiness tracking' },
            { n: '+ your upload', d: 'Same engine · your content stays yours' },
          ]" :key="e.n" class="reveal rounded-3xl border border-slate-200 bg-white p-5 transition hover:border-slate-400">
            <p class="font-semibold">{{ e.n }}</p>
            <p class="mt-1 text-sm text-slate-500">{{ e.d }}</p>
          </div>
        </div>

        <div class="mt-14 grid gap-4 md:grid-cols-2">
          <div class="reveal rounded-3xl border border-slate-200 bg-white p-8">
            <p class="font-display text-xl font-bold">Free</p>
            <p class="mt-1 text-sm text-slate-500">Everything you need to feel the engine.</p>
            <p class="mt-4 font-display text-4xl font-bold">$0</p>
            <ul class="mt-4 space-y-2 text-sm text-slate-600">
              <li>✓ 1 active exam</li>
              <li>✓ Adaptive drills + instant explanations</li>
              <li>✓ Daily explain challenges</li>
              <li>✓ Live readiness score</li>
            </ul>
            <button @click="getStarted" class="mt-6 w-full rounded-full bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white hover:bg-slate-700">Start free</button>
          </div>
          <div class="reveal rounded-3xl bg-slate-900 p-8 text-white">
            <p class="font-display text-xl font-bold">Pro <span class="ml-2 rounded-full bg-white/15 px-2 py-0.5 align-middle text-xs font-medium">coming soon</span></p>
            <p class="mt-1 text-sm text-slate-400">For serious exam seasons.</p>
            <p class="mt-4 font-display text-4xl font-bold">—</p>
            <ul class="mt-4 space-y-2 text-sm text-slate-300">
              <li>✓ Unlimited exams + private uploads</li>
              <li>✓ PDF syllabus & past-question import</li>
              <li>✓ Misconception review decks</li>
              <li>✓ AI-graded explanations + voice input</li>
            </ul>
            <button @click="getStarted" class="mt-6 w-full rounded-full bg-white px-6 py-2.5 text-sm font-semibold text-slate-900 hover:bg-slate-200">Join the waitlist</button>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="mx-auto max-w-3xl px-4 pb-20">
      <h2 class="reveal font-display text-3xl font-bold tracking-tight">FAQ</h2>
      <div class="mt-6 space-y-3">
        <details v-for="f in faqs" :key="f.q" class="reveal rounded-2xl border border-slate-200 bg-white p-4">
          <summary class="cursor-pointer font-medium">{{ f.q }}</summary>
          <p class="mt-2 text-sm text-slate-500">{{ f.a }}</p>
        </details>
      </div>
    </section>

    <!-- FINAL CTA -->
    <section class="mx-auto max-w-6xl px-4 pb-20">
      <div class="reveal rounded-[2rem] bg-slate-900 px-6 py-16 text-center text-white sm:py-20">
        <h2 class="mx-auto max-w-2xl font-display text-4xl font-bold tracking-tight sm:text-5xl">Read less. Know more. Pass.</h2>
        <p class="mx-auto mt-4 max-w-xl text-slate-400">Your exam date is fixed. Your preparation should be certain.</p>
        <button @click="getStarted" class="mt-8 rounded-full bg-white px-10 py-4 text-base font-semibold text-slate-900 transition hover:bg-slate-200">Start practicing free</button>
        <footer class="mx-auto mt-14 flex max-w-4xl flex-col items-center justify-between gap-3 border-t border-white/10 pt-6 text-sm text-slate-500 sm:flex-row">
          <span class="font-display font-bold text-white">Examficient<span class="text-emerald-400">.</span></span>
          <span>Read less, know more, pass exams.</span>
        </footer>
      </div>
    </section>
  </div>
</template>

<style scoped>
.reveal {
  opacity: 0;
  transform: translateY(24px);
  transition:
    opacity 0.7s ease,
    transform 0.7s ease;
}
.reveal.is-visible {
  opacity: 1;
  transform: none;
}
@media (prefers-reduced-motion: reduce) {
  .reveal {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
