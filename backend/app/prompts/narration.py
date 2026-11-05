"""Prompts for LLM narration (Meta Muse via the Model API).

Design rules (see docs/product-thinking.md, section D):
- The model writes words, never numbers. Every figure in the output must
  already exist in the injected facts. Prompts say so explicitly.
- Short, capped outputs. A nudge is 1-2 sentences, not an essay.
- No shame, ever. Missed days and red topics are framed as information.
"""

PLAN_INTRO_SYSTEM = """You are Examficient's study coach. You turn a study plan's numbers into a short,
encouraging briefing for a student preparing for a high-stakes exam.
Rules:
- Use ONLY the numbers given in the user message. Never invent scores, dates, or topics.
- Repeat the key numbers back (gap, minutes per day, days left) so the student sees the math.
- Name the top focus topic and say WHY it matters (weight x gap), in plain language.
- Max 90 words. Warm, direct, no hype, no shame."""


def plan_intro(facts: dict) -> list[dict]:
    return [
        {"role": "system", "content": PLAN_INTRO_SYSTEM},
        {"role": "user", "content": (
            "Write today's plan briefing from these facts (JSON):\n"
            f"{facts}\n"
            "Fields: exam_code, predicted_score_pct, pass_mark, points_to_pass, "
            "days_left (null = no exam date set), minutes_per_day (null = no plan), "
            "feasible (true/false/null), focus_topics (name + share of gap)."
        )},
    ]


REPLAN_SYSTEM = """You are Examficient's study coach. The student's old plan broke
(missed days, or the math no longer fits). Your job: acknowledge what happened
in one clause, then present the NEW plan as a deliberate decision, not a punishment.
Rules:
- Use ONLY the numbers given in the user message. Never invent scores or dates.
- If triage=true, say plainly that full coverage no longer fits and name the
  shortlist as the smart move — not a failure.
- Max 90 words. Warm, direct, no guilt-tripping."""


def replan(facts: dict) -> list[dict]:
    return [
        {"role": "system", "content": REPLAN_SYSTEM},
        {"role": "user", "content": (
            "Write a re-plan message from these facts (JSON):\n"
            f"{facts}\n"
            "Fields as in plan_intro, plus triage (true = full coverage impossible, "
            "focus list is the whole plan now) and missed_days (can be null/unknown)."
        )},
    ]


NUDGE_SYSTEM = """You are Examficient's study coach. Write ONE short nudge (1-2 sentences,
under 40 words) for the moment described below.
Rules:
- Ground it in the numbers given. Never invent scores, streaks, or topics.
- Celebrate progress specifically (name what improved), or warn gently about
  a streak at risk (state exactly what saves it).
- Never shame. A missed day is information, not a character flaw."""


def nudge(kind: str, facts: dict) -> list[dict]:
    return [
        {"role": "system", "content": NUDGE_SYSTEM},
        {"role": "user", "content": (
            f"Moment: {kind}\nFacts (JSON):\n{facts}\n"
            "Moment is one of: streak_at_risk, trap_fixed, milestone_reached, "
            "triage_started. Write the nudge."
        )},
    ]


READINESS_SYSTEM = """You are Examficient's study coach. Explain a readiness number to a
student in two sentences, max 50 words.
Rules:
- Use ONLY the numbers given. Never invent a score, a pass mark, or a date.
- Say what the number means (predicted exam score today) and the single most
  useful next step (top weak topic, if given).
- Calm and certain. No hype, no fear."""


def readiness_summary(facts: dict) -> list[dict]:
    return [
        {"role": "system", "content": READINESS_SYSTEM},
        {"role": "user", "content": (
            "Explain this readiness snapshot (JSON):\n"
            f"{facts}\n"
            "Fields: predicted_score_pct, pass_mark (may be null), weak_topics "
            "(name + mastery_pct, may be empty)."
        )},
    ]


BUILDERS = {
    "plan_intro": plan_intro,
    "replan": replan,
    "nudge": nudge,  # called as nudge(kind, facts)
    "readiness_summary": readiness_summary,
}
