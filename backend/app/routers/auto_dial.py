"""Auto-dial endpoints — find nearby places and start a sequential
outbound-call loop in the background.

The triage agent gets a `call_id` immediately; the frontend keeps polling
`/api/calls/{call_id}/status` and pushes contextual updates into the live
conversation as each attempt completes.
"""
from __future__ import annotations

import logging
from typing import List, Literal

from fastapi import APIRouter

from app.models.schemas import AutoDialRequest, AutoDialResponse, Place
from app.services.elevenlabs import call_service
from app.services.places import places_service

router = APIRouter(prefix="/api/auto-dial", tags=["auto-dial"])

logger = logging.getLogger(__name__)


def _callable_only(places: List[Place]) -> List[Place]:
    return [p for p in places if p.phone]


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

    callable_places = _callable_only(places)
    if not callable_places:
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
    record = await call_service.call_until_available(
        kind=kind,
        places=callable_places,
        context=context,
    )

    return AutoDialResponse(
        call_id=record.call_id,
        status=record.status,
        agent_type=kind,
        place=callable_places[0],
        total_attempts_planned=record.total_attempts_planned,
        message=(
            f"Started calling {len(callable_places)} {kind}(s) one by one. "
            "Keep talking with the user — you'll get a system update the "
            "moment any place answers or all calls are exhausted."
        ),
    )


@router.post("/vet", response_model=AutoDialResponse)
async def auto_dial_vet(req: AutoDialRequest) -> AutoDialResponse:
    return await _auto_dial("vet", req)


@router.post("/shelter", response_model=AutoDialResponse)
async def auto_dial_shelter(req: AutoDialRequest) -> AutoDialResponse:
    return await _auto_dial("foster", req)
