"""Auto-dial endpoints — combined "find nearest + call" in one shot.

The triage agent uses these instead of the two-step
`find_nearby_vets` → `call_vet` pattern. Less round-tripping, no risk
of the LLM losing the phone number between calls.
"""
from __future__ import annotations

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter

from app.models.schemas import AutoDialRequest, AutoDialResponse, Place
from app.services.elevenlabs import call_service
from app.services.places import places_service

router = APIRouter(prefix="/api/auto-dial", tags=["auto-dial"])

logger = logging.getLogger(__name__)


def _first_callable(places: List[Place]) -> Optional[Place]:
    for p in places:
        if p.phone:
            return p
    return None


async def _auto_dial(
    kind: Literal["vet", "foster"], req: AutoDialRequest
) -> AutoDialResponse:
    if kind == "vet":
        places = await places_service.search_vets(req.lat, req.lng, req.radius_m)
        default_context = "Injured animal needs urgent veterinary care"
    else:
        places = await places_service.search_foster(
            req.lat, req.lng, req.radius_m
        )
        default_context = "Rescued animal needs temporary foster care"

    target = _first_callable(places)
    if target is None:
        logger.info(
            "auto-dial %s — no callable result near (%s, %s)",
            kind,
            req.lat,
            req.lng,
        )
        return AutoDialResponse(
            status="no_results",
            agent_type=kind,
            message=(
                "No nearby option with a phone number was found. "
                "Try widening the search or asking the user for help."
            ),
        )

    context = req.context or default_context
    if kind == "vet":
        record = await call_service.call_vet(
            phone=target.phone or "",
            context=context,
            place_name=target.name,
        )
    else:
        record = await call_service.call_foster(
            phone=target.phone or "",
            context=context,
            place_name=target.name,
        )

    return AutoDialResponse(
        call_id=record.call_id,
        status=record.status,
        agent_type=kind,
        place=target,
    )


@router.post("/vet", response_model=AutoDialResponse)
async def auto_dial_vet(req: AutoDialRequest) -> AutoDialResponse:
    return await _auto_dial("vet", req)


@router.post("/shelter", response_model=AutoDialResponse)
async def auto_dial_shelter(req: AutoDialRequest) -> AutoDialResponse:
    return await _auto_dial("foster", req)
