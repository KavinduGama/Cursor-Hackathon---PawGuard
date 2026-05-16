"""Calls endpoints — spawn outbound vet / foster agents and poll status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import CallRequest, CallResponse, CallStatusResponse
from app.services.elevenlabs import call_service

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.post("/vet", response_model=CallResponse)
async def call_vet(req: CallRequest) -> CallResponse:
    record = await call_service.call_vet(
        phone=req.phone, context=req.context, place_name=req.place_name
    )
    return CallResponse(
        call_id=record.call_id, status=record.status, agent_type="vet"
    )


@router.post("/foster", response_model=CallResponse)
async def call_foster(req: CallRequest) -> CallResponse:
    record = await call_service.call_foster(
        phone=req.phone, context=req.context, place_name=req.place_name
    )
    return CallResponse(
        call_id=record.call_id, status=record.status, agent_type="foster"
    )


@router.get("/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(call_id: str) -> CallStatusResponse:
    record = await call_service.get_status(call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="call not found")
    return CallStatusResponse(
        call_id=record.call_id,
        status=record.status,
        summary=record.summary,
        available=record.available,
        wait_minutes=record.wait_minutes,
        notes=record.notes,
        attempts=record.attempts or None,
        successful_place=record.successful_place,
        current_attempt_index=record.current_attempt_index,
        total_attempts_planned=record.total_attempts_planned,
    )
