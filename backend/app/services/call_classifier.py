"""OpenAI-backed call-outcome classifier.

Given the transcript summary of an outbound call to a vet clinic or foster,
returns a strict JSON object describing the outcome — replacing the brittle
keyword heuristic in `elevenlabs.py`.

This is the *fallback* path: it only runs when the outbound agent did not
already produce structured data (via ElevenLabs dashboard "Evaluation
Criteria" / "Data Collection"), and only once per call.

If OPENAI_API_KEY is missing or the call fails, returns None — callers
should gracefully fall back to whatever signal they already have.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Literal, Optional, TypedDict

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"

_SYSTEM_INSTRUCTION = """You analyze a brief transcript summary of an
outbound phone call PawGuard (a pet-rescue dispatch system) just made to a
veterinary clinic or animal foster home. Your job is to extract a tight,
machine-readable outcome.

Always respond as a single JSON object — no markdown, no prose — with EXACTLY
these keys:

{
  "available": true | false | null,
  "wait_minutes": <integer> | null,
  "contact_name": "<person who answered, e.g. 'Dr. Jani'>" | null,
  "notes": "<one short sentence summary for the dispatcher>"
}

Rules:
- "available" = true ONLY if the place clearly confirmed they can accept or
  attend to the animal right now (or within a short, stated wait time).
- "available" = false if they declined, said they're closed/full/cannot help,
  no one answered, or the call went to voicemail.
- "available" = null only if the summary is too vague to tell.
- "wait_minutes" is the stated wait time in minutes if mentioned, else null.
- "contact_name" is the human contact named in the summary, else null.
- "notes" is at most one short sentence — what the dispatcher needs to know."""


class CallOutcome(TypedDict, total=False):
    available: Optional[bool]
    wait_minutes: Optional[int]
    contact_name: Optional[str]
    notes: Optional[str]


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class CallClassifier:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> Optional[AsyncOpenAI]:
        if self._client is not None:
            return self._client
        if not self._settings.OPENAI_API_KEY:
            return None
        self._client = AsyncOpenAI(api_key=self._settings.OPENAI_API_KEY)
        return self._client

    async def classify(
        self,
        kind: Literal["vet", "foster"],
        summary: str,
        place_name: Optional[str] = None,
    ) -> Optional[CallOutcome]:
        client = self._get_client()
        if client is None or not summary:
            return None

        model_name = self._settings.OPENAI_CLASSIFIER_MODEL or DEFAULT_MODEL
        place_label = place_name or ("the clinic" if kind == "vet" else "the foster")
        prompt = (
            f"Call kind: {kind}\n"
            f"Place: {place_label}\n"
            f"Transcript summary:\n{summary.strip()}"
        )

        try:
            resp = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=300,
            )
            raw = resp.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("call classifier request failed: %s", exc)
            return None

        return _parse_outcome(raw)


def _parse_outcome(raw: str) -> Optional[CallOutcome]:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(text)
        if not m:
            logger.warning("classifier returned non-JSON: %r", text[:200])
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            logger.warning("classifier JSON block unparseable: %r", text[:200])
            return None

    available = data.get("available")
    if available is not None and not isinstance(available, bool):
        available = None
    wait_minutes = data.get("wait_minutes")
    if isinstance(wait_minutes, str):
        try:
            wait_minutes = int(wait_minutes)
        except ValueError:
            wait_minutes = None
    if wait_minutes is not None and not isinstance(wait_minutes, int):
        wait_minutes = None
    contact_name = data.get("contact_name")
    if contact_name is not None and not isinstance(contact_name, str):
        contact_name = None
    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        notes = None
    return CallOutcome(
        available=available,
        wait_minutes=wait_minutes,
        contact_name=contact_name,
        notes=notes,
    )


call_classifier = CallClassifier()
