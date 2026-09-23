"""
Location resolution and geocoding for Indian districts, towns, villages, and shared pins.
Includes local seed cache, offline resilience, and Nominatim India-restricted geocoding.
"""
import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("app")

# Pre-seeded Indian districts, coastal hubs, and villages from official CAP drill areas
SEEDED_LOCATIONS: Dict[str, Dict[str, Any]] = {
    # Odisha
    "cuttack": {"name": "Cuttack", "district": "Cuttack", "state": "Odisha", "lat": 20.4625, "lon": 85.8830, "is_coastal": False},
    "puri": {"name": "Puri", "district": "Puri", "state": "Odisha", "lat": 19.8135, "lon": 85.8312, "is_coastal": True},
    "bhubaneswar": {"name": "Bhubaneswar", "district": "Khordha", "state": "Odisha", "lat": 20.2961, "lon": 85.8245, "is_coastal": False},
    "paradip": {"name": "Paradip", "district": "Jagatsinghpur", "state": "Odisha", "lat": 20.3165, "lon": 86.6114, "is_coastal": True},
    "ganjam": {"name": "Ganjam", "district": "Ganjam", "state": "Odisha", "lat": 19.3800, "lon": 85.0600, "is_coastal": True},
    "balasore": {"name": "Balasore", "district": "Balasore", "state": "Odisha", "lat": 21.4934, "lon": 86.9135, "is_coastal": True},
    "chandipur": {"name": "Chandipur", "district": "Balasore", "state": "Odisha", "lat": 21.4700, "lon": 87.0200, "is_coastal": True},
    "gopalpur": {"name": "Gopalpur", "district": "Ganjam", "state": "Odisha", "lat": 19.2600, "lon": 84.9100, "is_coastal": True},

    # Kerala
    "wayanad": {"name": "Wayanad", "district": "Wayanad", "state": "Kerala", "lat": 11.6854, "lon": 76.1320, "is_coastal": False},
    "kozhikode": {"name": "Kozhikode", "district": "Kozhikode", "state": "Kerala", "lat": 11.2588, "lon": 75.7804, "is_coastal": True},
    "ernakulam": {"name": "Ernakulam", "district": "Ernakulam", "state": "Kerala", "lat": 9.9816, "lon": 76.2999, "is_coastal": True},
    "idukki": {"name": "Idukki", "district": "Idukki", "state": "Kerala", "lat": 9.8500, "lon": 76.9700, "is_coastal": False},
    "munnar": {"name": "Munnar", "district": "Idukki", "state": "Kerala", "lat": 10.0889, "lon": 77.0595, "is_coastal": False},

    # Maharashtra
    "nagpur": {"name": "Nagpur", "district": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lon": 79.0882, "is_coastal": False},
    "mumbai": {"name": "Mumbai", "district": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777, "is_coastal": True},
    "ratnagiri": {"name": "Ratnagiri", "district": "Ratnagiri", "state": "Maharashtra", "lat": 16.9902, "lon": 73.3120, "is_coastal": True},

    # Tamil Nadu & Andhra
    "chennai": {"name": "Chennai", "district": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "is_coastal": True},
    "cuddalore": {"name": "Cuddalore", "district": "Cuddalore", "state": "Tamil Nadu", "lat": 11.7480, "lon": 79.7714, "is_coastal": True},
    "visakhapatnam": {"name": "Visakhapatnam", "district": "Visakhapatnam", "state": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185, "is_coastal": True},

    # North / Other Drill Districts
    "patna": {"name": "Patna", "district": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376, "is_coastal": False},
    "bikaner": {"name": "Bikaner", "district": "Bikaner", "state": "Rajasthan", "lat": 28.0229, "lon": 73.3119, "is_coastal": False},
    "uttarkashi": {"name": "Uttarkashi", "district": "Uttarkashi", "state": "Uttarakhand", "lat": 30.7268, "lon": 78.4354, "is_coastal": False},
}

# Runtime memory cache for geocoded queries
GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}


def resolve_location(
    query: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Resolve location from query string or coordinates.
    Returns (location_dict, is_ambiguous).
    """
    # 1. Coordinate Pin resolution
    if lat is not None and lon is not None:
        return _resolve_coordinates(lat, lon), False

    if not query or not query.strip():
        return None, True

    clean_q = query.strip().lower()

    # Remove filler words
    clean_q = re.sub(r'\b(in|near|at|around|for|weather|alert|forecast|here)\b', '', clean_q).strip()

    # 2. Check Seeded Locations
    for key, loc in SEEDED_LOCATIONS.items():
        if key in clean_q or clean_q in key:
            return loc, False

    # 3. Check Geocode Cache
    if clean_q in GEOCODE_CACHE:
        return GEOCODE_CACHE[clean_q], False

    # 4. Try Nominatim Geocoding (restricted to India)
    try:
        encoded = urllib.parse.quote(f"{clean_q}, India")
        url = f"https://nominatim.openstreetmap.org/search?q={encoded}&countrycodes=in&format=json&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SkySafeAI-DisasterApp/1.0 (contact: support@skysafe.gov.in)"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                res = data[0]
                display_name = res.get("display_name", "")
                parts = [p.strip() for p in display_name.split(",")]
                district = parts[-3] if len(parts) >= 3 else parts[0]
                state = parts[-2] if len(parts) >= 2 else "India"

                loc = {
                    "name": parts[0],
                    "district": district,
                    "state": state,
                    "lat": float(res["lat"]),
                    "lon": float(res["lon"]),
                    "is_coastal": False
                }
                GEOCODE_CACHE[clean_q] = loc
                return loc, False
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed for '{clean_q}': {e}")

    # Fallback to matching nearest seed if partial name matched
    for key, loc in SEEDED_LOCATIONS.items():
        if key.startswith(clean_q[:3]) and len(clean_q) >= 3:
            return loc, False

    # If completely unrecognized, mark ambiguous
    return None, True


def _resolve_coordinates(lat: float, lon: float) -> Dict[str, Any]:
    """Find the nearest seeded Indian location to the given lat/lon coordinates."""
    import math

    def dist(loc):
        return math.sqrt((loc["lat"] - lat) ** 2 + (loc["lon"] - lon) ** 2)

    nearest_key = min(SEEDED_LOCATIONS.keys(), key=lambda k: dist(SEEDED_LOCATIONS[k]))
    nearest = SEEDED_LOCATIONS[nearest_key]

    return {
        "name": f"Pin near {nearest['name']}",
        "district": nearest["district"],
        "state": nearest["state"],
        "lat": lat,
        "lon": lon,
        "is_coastal": nearest.get("is_coastal", False)
    }
