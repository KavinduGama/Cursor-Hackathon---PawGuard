"""Vision endpoints — start a session, stream frames, read cached observations."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FrameRequest,
    FrameResponse,
    ObservationResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.services.gemini import analysis_payload_to_dict, vision_service

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest) -> StartSessionResponse:
    sid = vision_service.start_session(req.session_id)
    return StartSessionResponse(session_id=sid)


@router.post("/analyze", response_model=FrameResponse)
async def analyze_frame(req: FrameRequest) -> FrameResponse:
    if not req.frame:
        raise HTTPException(status_code=400, detail="frame is required")
    session = await vision_service.analyze_frame(req.session_id, req.frame)
    return FrameResponse(
        frame_count=session.frame_count,
        analysis=analysis_payload_to_dict(session.latest_analysis),
    )


@router.get("/observations/{session_id}", response_model=ObservationResponse)
async def get_observations(session_id: str) -> ObservationResponse:
    session = await vision_service.get_session_or_restore(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return ObservationResponse(
        session_id=session.session_id,
        analysis=analysis_payload_to_dict(session.latest_analysis),
        frame_count=session.frame_count,
        severity=session.latest_severity,
        updated_at=session.updated_at,
    )


@router.delete("/session/{session_id}")
async def end_session(session_id: str) -> dict[str, str]:
    await vision_service.end_session(session_id)
    return {"status": "ended"}
