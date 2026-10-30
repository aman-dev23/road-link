"""Geographical distance and spatial calculations."""
from __future__ import annotations

import math

EARTH_RADIUS_M = 6371000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters using Haversine formula."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


def bounding_box(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    """Calculate min_lat, max_lat, min_lon, max_lon for a radius in meters."""
    delta_lat = math.degrees(radius_m / EARTH_RADIUS_M)
    # Cosine of latitude for longitude delta
    cos_lat = math.cos(math.radians(lat))
    if cos_lat > 0.00001:
        delta_lon = math.degrees(radius_m / (EARTH_RADIUS_M * cos_lat))
    else:
        delta_lon = 180.0

    min_lat = max(-90.0, lat - delta_lat)
    max_lat = min(90.0, lat + delta_lat)
    min_lon = max(-180.0, lon - delta_lon)
    max_lon = min(180.0, lon + delta_lon)

    return min_lat, max_lat, min_lon, max_lon

