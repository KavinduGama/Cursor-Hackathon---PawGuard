"""Pydantic request/response schemas for the PawGuard API."""
from __future__ import annotations

from typing import Any, List, Literal, Optional

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
    analysis: dict[str, Any]


class ObservationResponse(BaseModel):
    session_id: str
    analysis: dict[str, Any]
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


class CallAttemptSummary(BaseModel):
    place_name: str
    phone: str
    status: str  # completed | failed
    available: Optional[bool] = None
    wait_minutes: Optional[int] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None
    summary: Optional[str] = None


class CallStatusResponse(BaseModel):
    call_id: str
    # initiated | in_progress | completed | failed | exhausted | no_results
    status: str
    summary: Optional[str] = None
    available: Optional[bool] = None
    wait_minutes: Optional[int] = None
    contact_name: Optional[str] = None
    notes: Optional[str] = None
    # Loop-mode fields (populated when this call_id represents an
    # auto-dial sequential loop, not a single outbound call):
    attempts: Optional[List[CallAttemptSummary]] = None
    successful_place: Optional[Place] = None
    current_attempt_index: Optional[int] = None
    total_attempts_planned: Optional[int] = None


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
    # in_progress | no_results | failed
    status: str
    agent_type: Literal["vet", "foster"]
    place: Optional[Place] = None
    message: Optional[str] = None
    total_attempts_planned: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Dial-list (call a pre-selected list of places sequentially)
# ─────────────────────────────────────────────────────────────────────────────


class DialListRequest(BaseModel):
    kind: Literal["vet", "foster"] = "vet"
    places: List[Place] = Field(
        ..., min_length=1, description="Places to call, in order"
    )
    context: Optional[str] = None
    session_id: Optional[str] = None
