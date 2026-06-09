import math
import os
import time
from functools import lru_cache

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from schemas.conference import Coordinates


_geolocator = Nominatim(user_agent="conference-recommender/1.0", timeout=10)
_last_request_time: float = 0.0
_MIN_INTERVAL = 1.1  # Nominatim policy: max 1 request/second


def _rate_limit() -> None:
    """Ensure at least _MIN_INTERVAL seconds between Nominatim requests."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


@lru_cache(maxsize=256)
def geocode(address: str) -> Coordinates | None:
    """Geocode an address to coordinates. Results are cached so each unique
    address is only queried once — avoids hammering Nominatim with repeated
    lookups of the same user address across N conferences."""
    # Temporarily bypass the cluster HTTP proxy — Nominatim must be reached directly.
    saved = {k: os.environ.pop(k, None) for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")}
    try:
        _rate_limit()
        location = _geolocator.geocode(address)
        if location:
            return Coordinates(lat=location.latitude, lon=location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def haversine_km(a: Coordinates, b: Coordinates) -> float:
    R = 6371.0
    lat1, lon1 = math.radians(a.lat), math.radians(a.lon)
    lat2, lon2 = math.radians(b.lat), math.radians(b.lon)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(h))


def distance_to_score(km: float, max_km: float = 15_000.0) -> float:
    """Exponential decay: 0 km → 100, ~5000 km → ~50, max_km → ~0."""
    return round(100.0 * math.exp(-3.0 * km / max_km), 1)
