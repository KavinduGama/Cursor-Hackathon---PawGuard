"""ElevenLabs Conversational AI — outbound phone call manager.

Spawns vet / foster outbound call agents via ElevenLabs' Twilio integration.
Tracks the conversation status so the triage agent (Agent 1) can ask
"how did that call go?" and get a structured answer.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional

import httpx

from app.config import get_settings

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

    async def get_status(self, call_id: str) -> Optional[CallRecord]:
        record = self._calls.get(call_id)
        if record is None:
            return None
        if record.status not in {"completed", "failed"} and record.conversation_id:
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


async def _simulate_call(record: CallRecord, place_name: Optional[str]) -> None:
    """Used when ElevenLabs creds are missing — keeps demos working offline."""
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


call_service = ElevenLabsCallService()
