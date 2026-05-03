import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from ..schemas.conference import Coordinates


_geolocator = Nominatim(user_agent="conference-recommender/1.0", timeout=10)


def geocode(address: str) -> Coordinates | None:
    try:
        location = _geolocator.geocode(address)
        if location:
            return Coordinates(lat=location.latitude, lon=location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None


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
