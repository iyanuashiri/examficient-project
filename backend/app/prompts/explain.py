"""Prompts for explain-it-back grading (Meta Muse via the Model API).

The model grades HOW WELL the user explained, against the correct answer we
supply. It never sees anything but one question + one explanation, and it
never decides XP: it returns three 0-4 sub-scores as JSON, and the backend
sums them into score_10 and maps to XP. A failed parse means graded=false
and zero XP — never a guess at a reward.
"""

GRADE_SYSTEM = """You grade a student's written explanation of an exam question's concept.
Score three axes, each an integer 0-4:
- accuracy: is the mechanism/fact correct? 4 = fully correct, 0 = wrong or empty of content.
- completeness: are the key steps/reasons present? 4 = nothing important missing.
- own_words: is it paraphrased, not copied? 4 = clearly their own phrasing, 0 = verbatim copy of the answer.
Also write "feedback": one encouraging sentence (max 25 words) naming the single biggest gap, or praising the strongest point if all scores are 3+.
Reply with JSON ONLY, no other text: {"accuracy": n, "completeness": n, "own_words": n, "feedback": "..."}"""


def grade(stem: str, correct_text: str, user_text: str) -> list[dict]:
    return [
        {"role": "system", "content": GRADE_SYSTEM},
        {"role": "user", "content": (
            "Grade this explanation.\n"
            f"Question: {stem}\n"
            f"Correct answer: {correct_text}\n"
            f"Student explanation: {user_text}"
        )},
    ]
