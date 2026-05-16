"""Pydantic request/response schemas for the PawGuard API."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Vision
# ─────────────────────────────────────────────────────────────────────────────


class StartSessionRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None, description="Optional client-supplied session id"
    )


class StartSessionResponse(BaseModel):
    session_id: str
    status: str = "started"


class FrameRequest(BaseModel):
    session_id: str
    # data-URL or base64 encoded JPEG (e.g. "data:image/jpeg;base64,...")
    frame: str


class FrameResponse(BaseModel):
    status: str = "ok"
    frame_count: int
    analysis: str


class ObservationResponse(BaseModel):
    session_id: str
    analysis: str
    frame_count: int
    severity: Optional[str] = None
    updated_at: float


# ─────────────────────────────────────────────────────────────────────────────
# Location
# ─────────────────────────────────────────────────────────────────────────────


class LocationRequest(BaseModel):
    lat: float
    lng: float
    radius_m: int = 5000
    keyword: Optional[str] = None


class Place(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    rating: Optional[float] = None
    distance_m: Optional[float] = None
    place_id: str
    lat: float
    lng: float
    open_now: Optional[bool] = None


class PlacesResponse(BaseModel):
    results: List[Place]


# ─────────────────────────────────────────────────────────────────────────────
# Calls
# ─────────────────────────────────────────────────────────────────────────────


class CallRequest(BaseModel):
    phone: str = Field(..., description="E.164 phone number, e.g. +14155551234")
    context: str = Field(..., description="What the call agent should communicate")
    session_id: Optional[str] = None
    place_name: Optional[str] = None


class CallResponse(BaseModel):
    call_id: str
    status: str
    agent_type: Literal["vet", "foster"]


class CallStatusResponse(BaseModel):
    call_id: str
    status: str  # initiated | in_progress | completed | failed
    summary: Optional[str] = None
    available: Optional[bool] = None
    wait_minutes: Optional[int] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Auto-dial (find + call in one step)
# ─────────────────────────────────────────────────────────────────────────────


class AutoDialRequest(BaseModel):
    lat: float
    lng: float
    context: Optional[str] = None
    session_id: Optional[str] = None
    radius_m: int = 5000


class AutoDialResponse(BaseModel):
    call_id: Optional[str] = None
    status: str  # initiated | in_progress | failed | no_results
    agent_type: Literal["vet", "foster"]
    place: Optional[Place] = None
    message: Optional[str] = None
