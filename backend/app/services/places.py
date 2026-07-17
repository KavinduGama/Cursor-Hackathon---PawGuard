"""Google Places client — find nearby vets / foster care.

Uses the Places API (New) — places:searchNearby — which is the current
recommended endpoint. Falls back gracefully if no API key is configured
(returns a small set of demo data so the rest of the app remains demoable).
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional

import httpx

from app.config import get_settings
from app.models.schemas import Place

logger = logging.getLogger(__name__)

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.rating,places.internationalPhoneNumber,"
    "places.nationalPhoneNumber,places.currentOpeningHours.openNow"
)


class PlacesService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def api_key(self) -> str:
        return self._settings.GOOGLE_PLACES_API_KEY

    async def search_vets(
        self, lat: float, lng: float, radius_m: int = 5000
    ) -> List[Place]:
        # Test override — return a single fake clinic with a phone number
        # we control. Useful for end-to-end testing of the outbound call flow.
        if self._settings.MOCK_VET_PHONE:
            logger.info(
                "MOCK_VET_PHONE set — returning mock clinic %s",
                self._settings.MOCK_VET_PHONE,
            )
            return [
                Place(
                    place_id="mock-vet-1",
                    name=self._settings.MOCK_VET_NAME
                    or "PetCare Veterinary Hospital — Nawala",
                    address=self._settings.MOCK_VET_ADDRESS
                    or "47 Nawala Road, Nawala, Sri Lanka",
                    phone=self._settings.MOCK_VET_PHONE,
                    rating=5.0,
                    distance_m=300.0,
                    lat=lat + 0.001,
                    lng=lng + 0.001,
                    open_now=True,
                )
            ]
        return await self._search(
            lat,
            lng,
            radius_m,
            included_types=["veterinary_care"],
        )

    async def search_foster(
        self, lat: float, lng: float, radius_m: int = 8000
    ) -> List[Place]:
        # Google has no "foster care" type — proxy with animal shelters + rescues.
        return await self._search(
            lat,
            lng,
            radius_m,
            included_types=["animal_shelter", "pet_store"],
            keyword="animal rescue foster",
        )

    async def _search(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        included_types: List[str],
        keyword: Optional[str] = None,
    ) -> List[Place]:
        if not self.api_key:
            logger.warning("GOOGLE_PLACES_API_KEY missing — returning demo data")
            return _demo_places(lat, lng, included_types[0])

        body = {
            "includedTypes": included_types,
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        }
        if keyword:
            body["rankPreference"] = "DISTANCE"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }

        try:
            resp = await self._client.post(PLACES_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.exception("places search failed: %s", exc)
            return _demo_places(lat, lng, included_types[0])

        results: List[Place] = []
        for p in data.get("places", []):
            loc = p.get("location") or {}
            plat = loc.get("latitude", lat)
            plng = loc.get("longitude", lng)
            results.append(
                Place(
                    place_id=p.get("id", ""),
                    name=(p.get("displayName") or {}).get("text", "Unknown"),
                    address=p.get("formattedAddress", ""),
                    phone=p.get("internationalPhoneNumber")
                    or p.get("nationalPhoneNumber"),
                    rating=p.get("rating"),
                    lat=plat,
                    lng=plng,
                    distance_m=_haversine_m(lat, lng, plat, plng),
                    open_now=(p.get("currentOpeningHours") or {}).get("openNow"),
                )
            )

        results.sort(key=lambda r: r.distance_m or 1e12)
        return results


# ── helpers ─────────────────────────────────────────────────────────────────


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_DEMO_PHONE = "+94783870640"

_DEMO_VETS: tuple[tuple[str, str], ...] = (
    ("PetCare Veterinary Hospital — Nawala", "47 Nawala Road, Nawala, Sri Lanka"),
    ("Blue Paw Animal Clinic — Battaramulla", "18 Kaduwela Road, Battaramulla, Sri Lanka"),
    ("Metro Veterinary Centre — Colombo", "112 Thurstan Road, Colombo 07, Sri Lanka"),
)

_DEMO_SHELTERS: tuple[tuple[str, str], ...] = (
    ("Rainbow Rescue Animal Shelter — Dehiwala", "9 Station Road, Dehiwala, Sri Lanka"),
    ("Colombo Strays Welfare Shelter — Kirulapone", "25 Dutugemunu Street, Kirulapone, Sri Lanka"),
    ("Happy Tails Adoption Centre — Mount Lavinia", "61 Station Road, Mount Lavinia, Sri Lanka"),
)


def _demo_places(lat: float, lng: float, kind: str) -> List[Place]:
    """Tiny offline fallback so demos don't crash without an API key."""
    rows = _DEMO_VETS if kind == "veterinary_care" else _DEMO_SHELTERS
    return [
        Place(
            place_id=f"demo-{kind}-{i}",
            name=name,
            address=addr,
            phone=_DEMO_PHONE,
            rating=4.6 - i * 0.05,
            distance_m=420.0 * (i + 1),
            lat=lat + 0.001 * (i + 1),
            lng=lng + 0.001 * (i + 1),
            open_now=True,
        )
        for i, (name, addr) in enumerate(rows)
    ]


places_service = PlacesService()
