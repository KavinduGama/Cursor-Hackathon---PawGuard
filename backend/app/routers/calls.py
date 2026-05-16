"""Calls endpoints — spawn outbound vet / foster agents and poll status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AutoDialResponse,
    CallRequest,
    CallResponse,
    CallStatusResponse,
    DialListRequest,
)
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


@router.post("/dial-list", response_model=AutoDialResponse)
async def dial_list(req: DialListRequest) -> AutoDialResponse:
    """Accept a pre-selected list of places and call them one by one.

    Unlike auto-dial, this does NOT search Google Places — the caller
    provides the exact list (e.g. from a prior ``find_emergency_vet``).
    """
    callable_places = [p for p in req.places if p.phone]
    if not callable_places:
        return AutoDialResponse(
            status="no_results",
            agent_type=req.kind,
            message="None of the provided places have a phone number.",
        )

    default_ctx = (
        "Injured animal needs urgent veterinary care"
        if req.kind == "vet"
        else "Rescued animal needs temporary foster care"
    )
    record = await call_service.call_until_available(
        kind=req.kind,
        places=callable_places,
        context=req.context or default_ctx,
    )
    return AutoDialResponse(
        call_id=record.call_id,
        status=record.status,
        agent_type=req.kind,
        place=callable_places[0],
        total_attempts_planned=record.total_attempts_planned,
        message=(
            f"Started calling {len(callable_places)} {req.kind}(s) one by one. "
            "Keep talking with the user — you'll get a system update the "
            "moment any place answers or all calls are exhausted."
        ),
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
        contact_name=record.contact_name,
        notes=record.notes,
        attempts=record.attempts or None,
        successful_place=record.successful_place,
        current_attempt_index=record.current_attempt_index,
        total_attempts_planned=record.total_attempts_planned,
    )
