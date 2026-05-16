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
import uuid
from dataclasses import dataclass, field
from typing import List, Literal, Optional

import httpx

from app.config import get_settings
from app.models.schemas import CallAttemptSummary, Place

logger = logging.getLogger(__name__)

API_BASE = "https://api.elevenlabs.io/v1"


@dataclass
class CallRecord:
    call_id: str
    agent_type: Literal["vet", "foster"]
    conversation_id: Optional[str] = None
    status: str = "initiated"
    summary: Optional[str] = None
    available: Optional[bool] = None
    wait_minutes: Optional[int] = None
    notes: Optional[str] = None
    raw: dict = field(default_factory=dict)
    # Loop-mode fields (only populated for batch/looping records)
    attempts: List[CallAttemptSummary] = field(default_factory=list)
    successful_place: Optional[Place] = None
    current_attempt_index: Optional[int] = None
    total_attempts_planned: Optional[int] = None


_TERMINAL_STATUSES = {"completed", "failed", "exhausted", "no_results"}


class ElevenLabsCallService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._calls: dict[str, CallRecord] = {}

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
        asyncio.create_task(
            self._loop_until_available(record, kind, places, context)
        )
        return record

    async def get_status(self, call_id: str) -> Optional[CallRecord]:
        record = self._calls.get(call_id)
        if record is None:
            return None
        # Loop records advance themselves via the background task — only
        # individual outbound calls need a refresh poke here.
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

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": phone,
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
        # Best-effort parse of any structured "evaluation criteria" the agent
        # was configured to fill out.
        eval_result = analysis.get("evaluation_criteria_results") or {}
        if "available" in eval_result:
            record.available = bool(eval_result["available"].get("result") == "success")
        record.raw = data

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

                attempt = CallAttemptSummary(
                    place_name=place.name,
                    phone=place.phone or "",
                    status=single.status,
                    available=single.available,
                    wait_minutes=single.wait_minutes,
                    summary=single.summary,
                )
                record.attempts.append(attempt)

                if single.status == "completed" and single.available:
                    record.status = "completed"
                    record.available = True
                    record.successful_place = place
                    record.summary = single.summary
                    record.wait_minutes = single.wait_minutes
                    return

            record.status = "exhausted"
            record.notes = (
                f"Tried {len(record.attempts)} {kind}(s); none confirmed availability."
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("auto-dial loop crashed: %s", exc)
            record.status = "failed"
            record.notes = f"Loop crashed: {exc}"

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

        payload = {
            "agent_id": agent_id,
            "agent_phone_number_id": phone_number_id,
            "to_number": phone,
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
