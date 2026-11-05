"""Meta Model API client (https://dev.meta.ai/docs/sdks).

The Model API is OpenAI-compatible: we use the ``openai`` package pointed at
``https://api.meta.ai/v1`` with the Model API key passed explicitly. Default
model ``muse-spark-1.3`` (Standard mode: content is not used to train models).
Used ONLY for narration (words about numbers). It never computes, grades, or
ranks — see docs/product-thinking.md section D.
"""

from __future__ import annotations

import os

META_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3"
ASR_URL = "https://api.meta.ai/v1/asr/transcribe"
ASR_MODEL = "muse-voice-transcribe-1.0"


def _api_key() -> str | None:
    from app.core.config import settings

    return settings.meta_api_key or os.environ.get("MODEL_API_KEY") or None


def configured() -> bool:
    return bool(_api_key())


def complete(messages: list[dict], *, max_tokens: int = 400, timeout_s: float = 60.0) -> str:
    """One chat-completions call. Raises on any failure — callers fall back
    to deterministic template text, so narration degrades gracefully."""
    from openai import OpenAI

    key = _api_key()
    if not key:
        raise RuntimeError("Meta Model API key is not configured (META_API_KEY)")
    client = OpenAI(api_key=key, base_url=META_BASE_URL, timeout=timeout_s)
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        reasoning_effort="minimal",  # narration is a direct-answer task; see dev.meta.ai/docs/reasoning
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Empty completion from Meta Model API")
    return text


async def atranscribe(wav: bytes, *, timeout_s: float = 60.0) -> str:
    """Speech-to-text via Meta Muse Voice Transcribe (PUSH_TO_TALK).

    Takes mono 16-bit WAV bytes (16 or 24 kHz), returns the transcript.
    Raises on any failure — callers surface a retry, never an empty grade.
    """
    import httpx
    import json as _json

    key = _api_key()
    if not key:
        raise RuntimeError("Meta Model API key is not configured (META_API_KEY)")
    request_part = _json.dumps({"model": ASR_MODEL, "mode": "PUSH_TO_TALK", "audioEncoding": "WAV"})
    files = {
        "request": (None, request_part, "application/json"),
        "audio": ("audio.wav", wav, "audio/wav"),
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(ASR_URL, headers={"Authorization": f"Bearer {key}"}, files=files)
    if resp.status_code >= 400:
        raise RuntimeError(f"Transcription failed (HTTP {resp.status_code})")
    text = ((resp.json().get("transcript")) or "").strip()
    if not text:
        raise RuntimeError("Empty transcript from Meta Model API")
    return text
