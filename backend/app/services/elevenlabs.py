"""ElevenLabs Conversational AI — outbound phone call manager.

Spawns vet / foster outbound call agents via ElevenLabs' Twilio integration.
Tracks the conversation status so the triage agent (Agent 1) can ask
"how did that call go?" and get a structured answer.

Also supports a *sequential loop* mode (`call_until_available`): given a
list of places, dial them one by one in the background, stopping on the
first place that confirms availability. The loop is non-blocking — the
triage agent gets a `call_id` immediately and is expected to be notified
asynchronously by the frontend (which polls `get_call_status`).
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Literal, Optional

import time

import httpx

from app.config import get_settings
from app.models.schemas import CallAttemptSummary, Place
from app.services.call_classifier import call_classifier
from app import db

logger = logging.getLogger(__name__)

API_BASE = "https://api.elevenlabs.io/v1"

# Lightweight summary heuristics — used only when the outbound agent has no
# explicit `available` evaluation criterion configured on the ElevenLabs
# dashboard. Order matters: check NEGATIVE phrases first so "not available"
# isn't classified as available.
_UNAVAIL_PHRASES = (
    "not available",
    "unavailable",
    "no answer",
    "did not pick up",
    "didn't pick up",
    "voicemail",
    "closed",
    "cannot take",
    "can't take",
    "cannot help",
    "can't help",
    "unable to",
    "fully booked",
    "no vet",
    "no foster",
    "no one available",
    "declined",
)
_AVAIL_PHRASES = (
    "available",
    "can see",
    "can take",
    "will see",
    "is open",
    "we're open",
    "we are open",
    "confirmed",
    "bring her in",
    "bring him in",
    "bring it in",
    "bring the animal",
    "send the animal",
    "come on in",
    "come in",
)
_WAIT_RE = re.compile(r"(\d{1,3})\s*(?:min|minute)", re.I)


def _derive_available_from_summary(summary: Optional[str]) -> Optional[bool]:
    """Returns True/False if the summary text clearly indicates availability,
    otherwise None (unknown)."""
    if not summary:
        return None
    s = summary.lower()
    if any(p in s for p in _UNAVAIL_PHRASES):
        return False
    if any(p in s for p in _AVAIL_PHRASES):
        return True
    return None


def _extract_wait_minutes(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = _WAIT_RE.search(text)
    return int(m.group(1)) if m else None


def _data_collection_value(data_collection: dict, field_name: str):
    """ElevenLabs returns each data-collection field as either a raw value or
    a dict like {"value": "...", "rationale": "..."}. Normalise that."""
    node = data_collection.get(field_name)
    if isinstance(node, dict):
        return node.get("value")
    return node


def _pick_int(new_value, current):
    if new_value is None:
        return current
    if isinstance(new_value, int):
        return new_value
    if isinstance(new_value, str):
        try:
            return int(new_value.strip())
        except ValueError:
            return current
    return current


def _pick_str(new_value, current):
    if isinstance(new_value, str) and new_value.strip():
        return new_value.strip()
    return current


@dataclass
class CallRecord:
    call_id: str
    agent_type: Literal["vet", "foster"]
    conversation_id: Optional[str] = None
    status: str = "initiated"
    summary: Optional[str] = None
    available: Optional[bool] = None
    wait_minutes: Optional[int] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None
    raw: dict = field(default_factory=dict)
    classified: bool = False
    attempts: List[CallAttemptSummary] = field(default_factory=list)
    successful_place: Optional[Place] = None
    current_attempt_index: Optional[int] = None
    total_attempts_planned: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_TERMINAL_STATUSES = {"completed", "failed", "exhausted", "no_results"}


class ElevenLabsCallService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._calls: dict[str, CallRecord] = {}

    async def _persist(self, record: CallRecord) -> None:
        """Fire-and-forget save of a call record to SQLite."""
        record.updated_at = time.time()
        try:
            await db.upsert_call_record(
                call_id=record.call_id,
                agent_type=record.agent_type,
                status=record.status,
                conversation_id=record.conversation_id,
                summary=record.summary,
                available=record.available,
                wait_minutes=record.wait_minutes,
                contact_name=record.contact_name,
                notes=record.notes,
                classified=record.classified,
                attempts=[a.model_dump() for a in record.attempts] if record.attempts else None,
                successful_place=record.successful_place.model_dump() if record.successful_place else None,
                current_attempt_index=record.current_attempt_index,
                total_attempts_planned=record.total_attempts_planned,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to persist call record %s: %s", record.call_id, exc)

    async def _restore(self, call_id: str) -> Optional[CallRecord]:
        """Load a call record from the DB (e.g. after a restart)."""
        row = await db.load_call_record(call_id)
        if row is None:
            return None
        attempts = []
        for a in row.get("attempts") or []:
            attempts.append(CallAttemptSummary(**a))
        sp = row.get("successful_place")
        record = CallRecord(
            call_id=row["call_id"],
            agent_type=row["agent_type"],
            conversation_id=row.get("conversation_id"),
            status=row["status"],
            summary=row.get("summary"),
            available=row.get("available"),
            wait_minutes=row.get("wait_minutes"),
            contact_name=row.get("contact_name"),
            notes=row.get("notes"),
            classified=row.get("classified", False),
            attempts=attempts,
            successful_place=Place(**sp) if sp else None,
            current_attempt_index=row.get("current_attempt_index"),
            total_attempts_planned=row.get("total_attempts_planned"),
            created_at=row.get("created_at", 0),
            updated_at=row.get("updated_at", 0),
        )
        self._calls[call_id] = record
        return record

    # ── public API ───────────────────────────────────────────────────────
    async def call_vet(
        self, phone: str, context: str, place_name: Optional[str] = None
    ) -> CallRecord:
        return await self._spawn_call(
            agent_type="vet",
            agent_id=self._settings.ELEVENLABS_VET_AGENT_ID,
            phone=phone,
            context=context,
            place_name=place_name,
        )

    async def call_foster(
        self, phone: str, context: str, place_name: Optional[str] = None
    ) -> CallRecord:
        return await self._spawn_call(
            agent_type="foster",
            agent_id=self._settings.ELEVENLABS_FOSTER_AGENT_ID,
            phone=phone,
            context=context,
            place_name=place_name,
        )

    async def call_until_available(
        self,
        kind: Literal["vet", "foster"],
        places: List[Place],
        context: str,
    ) -> CallRecord:
        """Sequentially dial every callable place until one confirms
        availability. Returns immediately with an in-progress record;
        the loop runs in the background.
        """
        record = CallRecord(
            call_id=str(uuid.uuid4()),
            agent_type=kind,
            status="in_progress",
            total_attempts_planned=len(places),
            current_attempt_index=-1,
        )
        self._calls[record.call_id] = record
        await self._persist(record)
        asyncio.create_task(
            self._loop_until_available(record, kind, places, context)
        )
        return record

    async def get_status(self, call_id: str) -> Optional[CallRecord]:
        record = self._calls.get(call_id)
        if record is None:
            record = await self._restore(call_id)
        if record is None:
            return None
        if (
            record.total_attempts_planned is None
            and record.status not in _TERMINAL_STATUSES
            and record.conversation_id
        ):
            await self._refresh_status(record)
        return record

    # ── internals ────────────────────────────────────────────────────────
    async def _spawn_call(
        self,
        agent_type: Literal["vet", "foster"],
        agent_id: str,
        phone: str,
        context: str,
        place_name: Optional[str],
    ) -> CallRecord:
        call_id = str(uuid.uuid4())
        record = CallRecord(call_id=call_id, agent_type=agent_type)
        self._calls[call_id] = record

        api_key = self._settings.ELEVENLABS_API_KEY
        phone_number_id = self._settings.ELEVENLABS_PHONE_NUMBER_ID

        if not api_key or not agent_id or not phone_number_id:
            logger.warning(
                "ElevenLabs call config missing (api_key=%s agent_id=%s phone_id=%s) — "
                "simulating call",
                bool(api_key),
                bool(agent_id),
                bool(phone_number_id),
            )
            record.notes = "simulated (missing ElevenLabs config)"
            asyncio.create_task(_simulate_call(record, place_name))
            return record

        dial_phone = self._settings.DEMO_CALL_PHONE or phone
        if dial_phone != phone:
            logger.info("DEMO_CALL_PHONE active — dialling %s instead of real number", dial_phone)

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": dial_phone,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "context": context,
                    "place_name": place_name or "the clinic",
                    "agent_type": agent_type,
                }
            },
        }
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{API_BASE}/convai/twilio/outbound-call",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                record.conversation_id = data.get("conversation_id") or data.get(
                    "callSid"
                )
                record.status = "in_progress"
                record.raw = data
        except Exception as exc:  # noqa: BLE001
            logger.exception("outbound call failed: %s", exc)
            record.status = "failed"
            record.notes = f"Could not place the call: {exc}"

        await self._persist(record)
        return record

    async def _refresh_status(self, record: CallRecord) -> None:
        api_key = self._settings.ELEVENLABS_API_KEY
        if not api_key or not record.conversation_id:
            return
        url = f"{API_BASE}/convai/conversations/{record.conversation_id}"
        headers = {"xi-api-key": api_key}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("status refresh failed: %s", exc)
            return

        status = data.get("status", record.status)
        if status in {"done", "ended", "completed"}:
            record.status = "completed"
        analysis = data.get("analysis") or {}
        record.summary = (
            analysis.get("transcript_summary")
            or analysis.get("call_summary_title")
            or record.summary
        )

        # ── Path 1: structured output from the ElevenLabs dashboard ────────
        # Anything the user configures under "Evaluation Criteria" / "Data
        # Collection" on the outbound agent shows up here. We extract it
        # *first* — it's the cleanest, lowest-latency signal.
        eval_result = analysis.get("evaluation_criteria_results") or {}
        data_collection = analysis.get("data_collection_results") or {}

        derived: Optional[bool] = None
        avail_node = eval_result.get("available")
        if isinstance(avail_node, dict):
            result = avail_node.get("result")
            if result == "success":
                derived = True
            elif result == "failure":
                derived = False
            # result == "unknown" or anything else → leave as None
        if derived is None:
            call_successful = analysis.get("call_successful")
            if call_successful == "success":
                derived = True
            elif call_successful == "failure":
                derived = False
        if derived is not None:
            record.available = derived

        # Data-collection fields override the heuristics if dashboard-configured.
        record.wait_minutes = _pick_int(
            _data_collection_value(data_collection, "wait_minutes"),
            record.wait_minutes,
        )
        record.contact_name = _pick_str(
            _data_collection_value(data_collection, "contact_name"),
            record.contact_name,
        )
        record.notes = _pick_str(
            _data_collection_value(data_collection, "notes"),
            record.notes,
        )

        # ── Tertiary fallback: cheap keyword heuristic on the summary ──────
        # Only used if BOTH dashboard structured output AND (later) the LLM
        # classifier give nothing. Keeps the demo working even without an
        # GEMINI_API_KEY.
        if record.available is None:
            keyword_guess = _derive_available_from_summary(record.summary)
            if keyword_guess is not None:
                record.available = keyword_guess
        if record.wait_minutes is None:
            record.wait_minutes = _extract_wait_minutes(record.summary)

        record.raw = data
        await self._persist(record)

    async def _loop_until_available(
        self,
        record: CallRecord,
        kind: Literal["vet", "foster"],
        places: List[Place],
        context: str,
    ) -> None:
        """Background loop: try each place until one is `available=True`."""
        try:
            for idx, place in enumerate(places):
                record.current_attempt_index = idx

                # Spawn one outbound call. For the simulated path we want a
                # mix of unavailable/available results so the demo loop has
                # multiple narration beats — pass the loop index along.
                if kind == "vet":
                    single = await self._spawn_loop_call(
                        agent_type="vet",
                        agent_id=self._settings.ELEVENLABS_VET_AGENT_ID,
                        phone=place.phone or "",
                        context=context,
                        place_name=place.name,
                        loop_index=idx,
                        loop_total=len(places),
                    )
                else:
                    single = await self._spawn_loop_call(
                        agent_type="foster",
                        agent_id=self._settings.ELEVENLABS_FOSTER_AGENT_ID,
                        phone=place.phone or "",
                        context=context,
                        place_name=place.name,
                        loop_index=idx,
                        loop_total=len(places),
                    )

                # Wait for the single call to reach a terminal state.
                while single.status not in _TERMINAL_STATUSES:
                    await asyncio.sleep(2)
                    if single.conversation_id:
                        await self._refresh_status(single)

                # ── LLM classifier fallback (Path 2) ──────────────────────
                # If dashboard structured output + keyword heuristic still
                # couldn't determine availability (or to enrich missing
                # contact_name / wait_minutes), run the LLM classifier
                # exactly once per outbound call.
                needs_classify = (
                    single.status == "completed"
                    and not single.classified
                    and single.summary
                    and (
                        single.available is None
                        or single.contact_name is None
                        or single.wait_minutes is None
                    )
                )
                if needs_classify:
                    single.classified = True
                    outcome = await call_classifier.classify(
                        kind=kind,
                        summary=single.summary or "",
                        place_name=place.name,
                    )
                    if outcome:
                        if single.available is None and outcome.get("available") is not None:
                            single.available = outcome["available"]
                        if single.wait_minutes is None and outcome.get("wait_minutes") is not None:
                            single.wait_minutes = outcome["wait_minutes"]
                        if not single.contact_name and outcome.get("contact_name"):
                            single.contact_name = outcome["contact_name"]
                        if not single.notes and outcome.get("notes"):
                            single.notes = outcome["notes"]

                attempt = CallAttemptSummary(
                    place_name=place.name,
                    phone=place.phone or "",
                    status=single.status,
                    available=single.available,
                    wait_minutes=single.wait_minutes,
                    contact_name=single.contact_name,
                    notes=single.notes,
                    summary=single.summary,
                )
                record.attempts.append(attempt)
                await self._persist(record)

                if single.status == "completed" and single.available:
                    record.status = "completed"
                    record.available = True
                    record.successful_place = place
                    record.summary = single.summary
                    record.wait_minutes = single.wait_minutes
                    record.contact_name = single.contact_name
                    record.notes = single.notes
                    await self._persist(record)
                    return

            record.status = "exhausted"
            record.notes = (
                f"Tried {len(record.attempts)} {kind}(s); none confirmed availability."
            )
            await self._persist(record)
        except Exception as exc:  # noqa: BLE001
            logger.exception("auto-dial loop crashed: %s", exc)
            record.status = "failed"
            record.notes = f"Loop crashed: {exc}"
            await self._persist(record)

    async def _spawn_loop_call(
        self,
        agent_type: Literal["vet", "foster"],
        agent_id: str,
        phone: str,
        context: str,
        place_name: Optional[str],
        loop_index: int,
        loop_total: int,
    ) -> CallRecord:
        """Same as _spawn_call but routes simulation through the loop-aware
        simulator so the demo produces mixed unavailable/available results.
        """
        call_id = str(uuid.uuid4())
        record = CallRecord(call_id=call_id, agent_type=agent_type)
        self._calls[call_id] = record

        api_key = self._settings.ELEVENLABS_API_KEY
        phone_number_id = self._settings.ELEVENLABS_PHONE_NUMBER_ID

        if not api_key or not agent_id or not phone_number_id:
            record.notes = "simulated (missing ElevenLabs config)"
            asyncio.create_task(
                _simulate_loop_call(record, place_name, loop_index, loop_total)
            )
            return record

        dial_phone = self._settings.DEMO_CALL_PHONE or phone

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": dial_phone,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "context": context,
                    "place_name": place_name or "the clinic",
                    "agent_type": agent_type,
                }
            },
        }
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{API_BASE}/convai/twilio/outbound-call",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                record.conversation_id = data.get("conversation_id") or data.get(
                    "callSid"
                )
                record.status = "in_progress"
                record.raw = data
        except Exception as exc:  # noqa: BLE001
            logger.exception("loop outbound call failed: %s", exc)
            record.status = "failed"
            record.notes = f"Could not place the call: {exc}"

        await self._persist(record)
        return record


async def _simulate_call(record: CallRecord, place_name: Optional[str]) -> None:
    """Used when ElevenLabs creds are missing — keeps single-call demos working offline."""
    await asyncio.sleep(3)
    record.status = "completed"
    if record.agent_type == "vet":
        record.available = True
        record.wait_minutes = 15
        record.summary = (
            f"Spoke with {place_name or 'the clinic'}. Dr. Smith can see the "
            "animal in 15 minutes. Bring it straight in."
        )
    else:
        record.available = True
        record.summary = (
            f"{place_name or 'Happy Paws Foster'} can take the animal. They can "
            "arrange pickup in about 30 minutes."
        )


async def _simulate_loop_call(
    record: CallRecord,
    place_name: Optional[str],
    loop_index: int,
    loop_total: int,
) -> None:
    """Loop-mode simulation: produces a fail / fail / success cadence so the
    demo's contextual updates feel realistic. The very last place always
    succeeds; intermediate places alternate between "no answer" and "closed".
    """
    await asyncio.sleep(2.5)
    record.status = "completed"

    is_last = loop_index >= loop_total - 1
    # Always succeed on the last attempt; otherwise simulate unavailability
    # for the first one or two so the agent narrates progress.
    if is_last or loop_index >= 2:
        record.available = True
        if record.agent_type == "vet":
            record.wait_minutes = 15
            record.summary = (
                f"{place_name or 'the clinic'} confirmed — they can see the "
                "animal in about 15 minutes."
            )
        else:
            record.summary = (
                f"{place_name or 'Happy Paws Foster'} can take the animal. "
                "Pickup in around 30 minutes."
            )
        return

    record.available = False
    if loop_index == 0:
        record.summary = f"No answer at {place_name or 'the clinic'}."
    else:
        record.summary = f"{place_name or 'the clinic'} is closed right now."


call_service = ElevenLabsCallService()
