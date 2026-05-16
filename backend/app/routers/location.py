"""Location endpoints — nearby vets and foster care."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import LocationRequest, PlacesResponse
from app.services.places import places_service

router = APIRouter(prefix="/api/location", tags=["location"])


@router.post("/vets", response_model=PlacesResponse)
async def find_vets(req: LocationRequest) -> PlacesResponse:
    results = await places_service.search_vets(req.lat, req.lng, req.radius_m)
    return PlacesResponse(results=results)


@router.post("/foster", response_model=PlacesResponse)
async def find_foster(req: LocationRequest) -> PlacesResponse:
    results = await places_service.search_foster(req.lat, req.lng, req.radius_m)
    return PlacesResponse(results=results)
