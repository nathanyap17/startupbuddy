"""Google Places API (New): geocode a Malaysian place and find nearby competitors.

Auth: MAPS_API_KEY if set, otherwise OAuth via Application Default Credentials
(Places API (New) accepts OAuth bearer tokens + X-Goog-User-Project)."""
import asyncio
import math
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from app.config import settings

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ("places.displayName,places.formattedAddress,places.rating,places.userRatingCount,"
          "places.location,places.googleMapsUri,places.primaryTypeDisplayName,places.priceLevel")
_creds = None


def _auth_headers() -> dict[str, str]:
    global _creds
    if settings.maps_api_key:
        return {"X-Goog-Api-Key": settings.maps_api_key}
    if _creds is None:
        _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _creds.valid:
        _creds.refresh(google.auth.transport.requests.Request())
    return {"Authorization": f"Bearer {_creds.token}", "X-Goog-User-Project": settings.google_cloud_project}


async def _search(body: dict[str, Any]) -> list[dict[str, Any]]:
    headers = await asyncio.to_thread(_auth_headers)
    headers |= {"X-Goog-FieldMask": FIELDS, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(SEARCH_URL, json=body, headers=headers)
        r.raise_for_status()
        return r.json().get("places", [])


def _km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    p = math.pi / 180
    h = (math.sin((b_lat - a_lat) * p / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lng - a_lng) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


async def geocode(location_text: str) -> dict[str, Any] | None:
    places = await _search({"textQuery": f"{location_text}, Malaysia", "regionCode": "MY", "pageSize": 1})
    if not places:
        return None
    p = places[0]
    return {"name": p.get("displayName", {}).get("text", location_text), "address": p.get("formattedAddress", ""),
            "lat": p["location"]["latitude"], "lng": p["location"]["longitude"]}


async def nearby_competitors(query: str, lat: float, lng: float, radius_m: int = 1000) -> list[dict[str, Any]]:
    body = {"textQuery": query, "regionCode": "MY", "pageSize": 15,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius_m)}}}
    out = []
    for p in await _search(body):
        loc = p.get("location", {})
        dist = _km(lat, lng, loc.get("latitude", lat), loc.get("longitude", lng))
        out.append({
            "name": p.get("displayName", {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount"),
            "type": p.get("primaryTypeDisplayName", {}).get("text"),
            "distance_km": round(dist, 2),
            "maps_url": p.get("googleMapsUri"),
        })
    return sorted(out, key=lambda x: x["distance_km"])
