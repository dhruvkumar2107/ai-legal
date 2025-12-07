# nearby.py
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from haversine import haversine, Unit
from typing import List, Dict, Optional

geolocator = Nominatim(user_agent="nyaysathi_nearby")
geocode_multi = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=2, error_wait_seconds=2)

def geocode_location(text: str) -> Optional[Dict]:
    """Return dict with lat, lon, address for a pincode/city string."""
    try:
        loc = geocode_multi(text + ", India")
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "address": loc.address}
    except Exception:
        return None
    return None

def nearby_search(query: str, lat: float, lon: float, limit: int = 5) -> List[Dict]:
    """
    Best-effort search using Nominatim. Returns list of {name, address, lat, lon, distance_km}.
    This is for demo purposes; for production use Google Places API.
    """
    results = []
    # try search variants
    tries = [
        f"{query} near {lat},{lon}",
        f"{query} near India",
        f"{query} {lat} {lon}"
    ]
    places = None
    for q in tries:
        try:
            places = geolocator.geocode(q, exactly_one=False, limit=limit*2)
            if places:
                break
        except Exception:
            places = None

    if not places:
        # fallback: search query + country
        try:
            places = geolocator.geocode(f"{query} India", exactly_one=False, limit=limit*2)
        except Exception:
            places = None

    if places:
        for p in places:
            try:
                plat, plon = float(p.latitude), float(p.longitude)
                dist = haversine((lat, lon), (plat, plon), unit=Unit.KILOMETERS)
                results.append({
                    "name": getattr(p, "raw", {}).get("display_name", str(query)),
                    "address": getattr(p, "raw", {}).get("display_name", "") or p.address or "",
                    "lat": plat,
                    "lon": plon,
                    "distance_km": round(dist, 2)
                })
            except Exception:
                continue

    # dedupe and sort
    uniq = {}
    for r in results:
        key = (round(r["lat"], 5), round(r["lon"], 5))
        if key not in uniq or uniq[key]["distance_km"] > r["distance_km"]:
            uniq[key] = r
    out = sorted(list(uniq.values()), key=lambda x: x["distance_km"])[:limit]
    return out
