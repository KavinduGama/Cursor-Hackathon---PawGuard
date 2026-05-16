"""Gemini-backed vision service.

Maintains one chat session per session_id so Gemini carries memory across
frames ("the swelling I noticed 30s ago is worse now"). The most recent
analysis is cached so the voice agent can read it instantly.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app import db

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """You are PawGuard's vision module — a calm, expert
animal-rescue triage assistant viewing live video frames from a phone camera.

You will receive frames from the same incident over time. For each frame,
respond in tight JSON:

{
  "animal": "<species/breed if visible, else 'unknown'>",
  "visible_injuries": ["short bullet", "..."],
  "severity": "CRITICAL|MODERATE|MILD|UNKNOWN",
  "changes_since_last": "<short note, '' if first frame or no change>",
  "guidance": "<one short instruction for the human, e.g. 'show the other side'>",
  "confidence": 0.0-1.0
}

Severity rubric:
- CRITICAL: heavy bleeding, exposed bone, unresponsive, severe limp, breathing distress
- MODERATE: visible wound, limping, lethargy, swelling
- MILD: minor scrape, irritation, dirty but otherwise alert
- UNKNOWN: cannot see animal clearly

Be concise. JSON only — no markdown, no prose."""


@dataclass
class VisionSession:
    session_id: str
    chat: any  # google.genai chat session
    latest_analysis: str = ""
    latest_severity: str = "UNKNOWN"
    frame_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class GeminiVisionService:
    """In-process registry of vision sessions + Gemini calls."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._sessions: dict[str, VisionSession] = {}
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self._settings.GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            self._client = genai.Client(api_key=self._settings.GEMINI_API_KEY)
        return self._client

    @property
    def _model(self) -> str:
        return self._settings.GEMINI_MODEL or DEFAULT_MODEL

    # ── session management ───────────────────────────────────────────────
    def start_session(self, session_id: Optional[str] = None) -> str:
        sid = session_id or str(uuid.uuid4())
        client = self._get_client()
        chat = client.chats.create(
            model=self._model,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        now = time.time()
        self._sessions[sid] = VisionSession(
            session_id=sid, chat=chat, created_at=now, updated_at=now,
        )
        asyncio.get_event_loop().create_task(
            db.upsert_vision_session(sid, "", "UNKNOWN", 0, now, now)
        )
        logger.info("vision session started id=%s model=%s", sid, self._model)
        return sid

    async def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        await db.delete_vision_session(session_id)

    def get_session(self, session_id: str) -> Optional[VisionSession]:
        return self._sessions.get(session_id)

    async def get_session_or_restore(self, session_id: str) -> Optional[VisionSession]:
        """Return from cache, or restore from DB if the backend restarted.

        Note: a restored session won't have a live Gemini chat — it can only
        serve the cached latest_analysis. A new start_session() call is
        needed to resume live frame analysis.
        """
        session = self._sessions.get(session_id)
        if session is not None:
            return session
        row = await db.load_vision_session(session_id)
        if row is None:
            return None
        session = VisionSession(
            session_id=session_id,
            chat=None,
            latest_analysis=row["analysis"],
            latest_severity=row["severity"],
            frame_count=row["frame_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        self._sessions[session_id] = session
        return session

    # ── frame analysis ───────────────────────────────────────────────────
    async def analyze_frame(self, session_id: str, frame_b64: str) -> VisionSession:
        session = self._sessions.get(session_id)
        if session is None:
            sid = self.start_session(session_id)
            session = self._sessions[sid]

        if session.chat is None:
            client = self._get_client()
            session.chat = client.chats.create(
                model=self._model,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )

        image_bytes = _decode_data_url(frame_b64)

        async with session.lock:
            prompt = (
                "New frame. Analyze it. If you've seen previous frames in "
                "this session, comment on changes_since_last."
            )

            def _send() -> str:
                resp = session.chat.send_message(
                    [
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        prompt,
                    ]
                )
                return resp.text or ""

            try:
                text = await asyncio.to_thread(_send)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Gemini frame analysis failed: %s", exc)
                text = (
                    '{"animal":"unknown","visible_injuries":[],"severity":"UNKNOWN",'
                    '"changes_since_last":"","guidance":"Hold camera steady",'
                    '"confidence":0.0}'
                )

            session.latest_analysis = text.strip()
            session.latest_severity = _extract_severity(text)
            session.frame_count += 1
            session.updated_at = time.time()

            asyncio.get_event_loop().create_task(
                db.upsert_vision_session(
                    session.session_id,
                    session.latest_analysis,
                    session.latest_severity,
                    session.frame_count,
                    session.updated_at,
                    session.created_at,
                )
            )
            return session


# ── helpers ─────────────────────────────────────────────────────────────────

_DATA_URL_RE = re.compile(r"^data:image/[a-zA-Z]+;base64,")


def _decode_data_url(frame: str) -> bytes:
    """Accept either a raw base64 string or a data: URL."""
    clean = _DATA_URL_RE.sub("", frame, count=1)
    return base64.b64decode(clean)


_SEVERITY_RE = re.compile(r'"severity"\s*:\s*"(CRITICAL|MODERATE|MILD|UNKNOWN)"')


def _extract_severity(text: str) -> str:
    m = _SEVERITY_RE.search(text or "")
    return m.group(1) if m else "UNKNOWN"


vision_service = GeminiVisionService()
