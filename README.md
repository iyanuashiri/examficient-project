# Examficient

**Read less. Know more. Pass exams.**

Examficient is an adaptive exam-prep app: multiple-choice drills drive a per-user
mastery profile, misconception-level diagnosis, readiness scoring against the
real pass mark — plus explain-it-back challenges graded by AI, drill rooms, and
a study coach that talks like it knows you. Coverage starts with Nigeria (JAMB,
WAEC), the US (SAT, GRE), the UK (A-Levels), and AWS certifications.

- **Backend:** FastAPI + SQLAlchemy (SQLite locally, Postgres via `DATABASE_URL`)
- **Frontend:** Vue 3 + Vite + Tailwind v4
- **AI:** Meta Model API — Muse Spark (narration + grading), Muse Voice Transcribe (voice input)

---

## 1. Features

### Adaptive practice engine

- **Next-question picker** holds every question at the edge of your ability (~70%
  pass chance): Elo-style theta + per-question difficulty calibration (gated on
  ≥5 answers) + guess/slip detection from response time.
- **Distractor diagnosis** — every wrong option maps to a misconception; misses
  surface as "Trap to watch" with per-option explanations after each answer.
- **Retry queue** — miss a trap, get re-tested on the same misconception later.
- **Forgetting-aware scheduling** — `next_review_at` resurfacing per topic.

### Mastery & readiness

- Per-topic mastery (0–100%), exam-level **predicted score vs `pass_mark`**
  ("12 points to go"), daily-minutes study plan with **triage mode** when the
  math no longer fits the deadline.
- Readiness snapshots (one row per user/exam/day) power the Analytics trajectory
  curve, topic breakdowns, and misconception ledger.

### Explain-it-back challenges (AI-graded)

- **Daily challenges** — 3 engine-picked questions from your weakest topics,
  deterministic per day so everyone shares one set.
- **Weekly showdown** — your 5 hardest questions of the week, locked until the
  week's last day.
- You explain the concept in writing (or out loud); the LLM grades
  accuracy/completeness/own-words and the **backend** sums to a score → XP.
- **Hard rules:** grading feeds XP/leaderboard only — never mastery, readiness,
  or calibration. Copy-paste and one-liners are gated before any LLM call;
  30 XP/day cap; LLM failure = zero XP, never a guess.

### Voice input (exam-gated)

- Mic → browser-encoded WAV → `POST /practice/transcribe/` → Meta Muse Voice
  Transcribe (`PUSH_TO_TALK`) → transcript travels the identical grading path.
- Voice is a **property of the exam**: listening/speaking exams (SAT Reading &
  Writing) get a live mic; written exams (JAMB, WAEC) show it disabled by design.

### AI coach narration

- A Meta model writes **words about numbers we computed** — plan briefings,
  re-plans when life happens, streak/trap/milestone nudges — rendered in the
  Dashboard focus card and practice mission banner.
- Template fallback when the key is missing or the call fails; the feature
  degrades, never breaks.

### Drill rooms + leagues

- Window-based rooms (no presence tracking): answering inside the window = you're
  in. Official weekly mocks per exam + user-created rooms, shareable links,
  per-room stats, hardest-questions, and leaderboards.
- Weekly effort leagues (XP only — **rank effort, never ability**), streaks,
  levels, cohort countdowns.

### Content

- Certifications → exams → syllabi → topics → questions → options →
  misconceptions; admin CRUD + bulk topic upsert; private uploads run the same
  engine. Featured exams are admin-curated; users enroll to prepare.

---

## 2. Repository layout

```
backend/
  app/
    api/routes/      # exams, practice, rooms (+practice_extra), users, certifications
    core/            # config (.env), database, security
    crud/            # practice engine, social (stats/rooms/plan), narration, explain, challenge
    models/          # exam, practice (attempts, mastery, explain), room, user
    prompts/         # narration.py, explain.py — LLM prompts live here, versioned
    schemas/         # pydantic I/O per domain
    llm.py           # Meta Model API client (chat + transcription)
  alembic/versions/  # migrations (apply in order)
  seed_all.py        # featured shelf + JAMB-BIO bank + demo users + rooms
  seed_data_bio.py   # 24 JAMB-style biology questions, topics, misconceptions
frontend-vue/
  src/
    views/           # Landing, Dashboard, Practice, Challenges, Rooms, Analytics, …
    api/             # client.js (token, timeouts), voice.js (mic → WAV)
    router/ App.vue  # sidebar shell: Dashboard · Exams · Rooms · Challenges · Analytics · Profile
docs/
  api.md             # endpoint reference
  features.md        # feature inventory (done / next / later)
  product-thinking.md# design rules the code follows
  frontend-todo.md   # UI backlog
```

---

## 3. Quickstart

### Prereqs

- Python via [uv](https://docs.astral.sh/uv/), Node 18+.

### Backend

```powershell
cd backend
uv sync

# .env (same folder)
# SECRET_KEY=change-me
# META_API_KEY=your-model-api-key      # narration, grading, transcription (optional: features fall back without it)
# DATABASE_URL=                         # empty = local SQLite examficient.db

uv run alembic upgrade head     # apply migrations
uv run python seed_all.py       # featured exams + demo users + weekly rooms
uv run fastapi dev app/main.py  # serves http://localhost:8000 (docs at /docs)
```

Seed notes:

- Register `iyanu@example.com` first — seeding promotes it to admin.
- `--reset` wipes content tables (users kept) for a clean reseed.
- Demo users (`password123`) arrive with spread-out JAMB-BIO activity so
  leaderboards and rooms are alive on first login.

### Frontend

```powershell
cd frontend-vue
npm install
npm run dev    # http://localhost:5173 (Vite proxies nothing; CORS allows it)
npm run build  # production build — keep this green before every demo
```

### Environment variables

| Var | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | yes | JWT signing |
| `META_API_KEY` (`MODEL_API_KEY` fallback) | for AI features | Muse Spark + Voice Transcribe; everything falls back to deterministic text without it |
| `DATABASE_URL` | no | Postgres in production; empty = local SQLite |
| `EXAMFICIENT_SQLITE_FILE_NAME` | no | SQLite filename (default `examficient.db`) |
| `AWS_*`, `DB_SECRET_ARNS` | prod only | RDS Secrets Manager + region |

---

## 4. API overview

Auth is Bearer JWT (`POST /auth/login/`). Full reference in `docs/api.md`.

| Area | Highlights |
|---|---|
| Practice | `GET next/`, `POST answer/`, `GET readiness/`, `GET plan/`, `GET stats/`, `GET history/` |
| Challenges | `GET challenges/` (daily + weekly board), `POST explain/`, `GET explain/history/`, `POST transcribe/` |
| Narration | `POST narrate/` (`plan_intro` / `replan` / `nudge` / `readiness_summary`) |
| Rooms | `GET official/` · `mine/` · `?exam_id=`, `POST /`, `GET {id}/stats/`, `GET {id}/leaderboard/` |
| Content | `POST /exams/` (`voice_enabled` flag), enroll/leave, syllabi/topics/questions CRUD |
| Meta | `GET analytics/`, `GET cohort/`, `GET leaderboard/`, certifications |

---

## 5. Design rules (the ones judges ask about)

1. **The LLM writes words, never numbers.** Mastery, readiness, difficulty, and XP
   math are deterministic; the model only narrates or grades inside a rubric —
   and the backend, not the model, sums sub-scores into rewards.
2. **Engines degrade, never break.** No key, offline, or failed call → template
   text or `graded=false` with zero XP. The practice loop never depends on AI.
3. **Rank effort, never ability.** Leaderboards and rooms use XP and streaks;
   mastery and predicted scores are private to the learner.
4. **Voice is exam-gated.** Speaking is the skill on listening/speaking exams
   and a gimmick on written ones — the flag lives on the exam, and the UI says so.
5. **No review queues, no presence.** Ingestion owns quality; room membership is
   inferred from answers in the window. Fewer states, fewer bugs.

---

## 6. Five-minute demo script

1. **Landing** — run the 60-second interactive demo; miss one on purpose to show
   trap diagnosis.
2. **Practice JAMB-BIO** — answer, open "Explain it back", submit a one-line
   explanation (gated) then a real one (graded + XP).
3. **Challenges** — today's 3 daily picks; scroll to the locked weekly showdown;
   hover the disabled mic on JAMB-BIO, then open SAT-RW where it's live.
4. **Rooms** — open the weekly mock: 7 participants, live leaderboard, your rank.
5. **Dashboard/Analytics** — readiness vs pass mark, trajectory curve, plan that
   re-plans when you fall behind.

---

## 7. Verification

- Frontend: `npm run build` must pass before any demo or push.
- Backend: features are verified with throwaway TestClient suites (isolated
  in-memory DB) covering gates, grading, XP wiring, and fallbacks; dev DB is
  migrated with `alembic upgrade head` and exercised against live data.
- Live Meta paths (narration, grading, transcription) verified against the real
  API with `META_API_KEY` set; all survive key-missing/offline by design.

## 8. Roadmap

- Friend streaks (opt-in, no-shame: streaks, never scores)
- Ingestion pipeline (PDF syllabus + past-question import at scale)
- Nigeria pack (offline mode, parent reports, CBT skin)
- Paywall (Pro: unlimited exams, uploads, AI grading volume)

---

Built by Iyanuoluwa Ajao. Git history is curated by the author — please don't
push from agents; open a PR description instead.
