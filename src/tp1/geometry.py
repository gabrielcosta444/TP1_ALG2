
from math import asin, cos, isfinite, radians, sin, sqrt

from tp1.models import Coordinate

EARTH_RADIUS_KM = 6371.0088


def haversine_km(origin: Coordinate, destination: Coordinate) -> float:
    latitude_delta = radians(destination.latitude - origin.latitude)
    longitude_delta = radians(destination.longitude - origin.longitude)
    origin_latitude = radians(origin.latitude)
    destination_latitude = radians(destination.latitude)

    haversine = sin(latitude_delta / 2.0) ** 2 + (
        cos(origin_latitude)
        * cos(destination_latitude)
        * sin(longitude_delta / 2.0) ** 2
    )
    central_angle = 2.0 * asin(sqrt(min(1.0, max(0.0, haversine))))
    return EARTH_RADIUS_KM * central_angle


def estimate_eta_minutes(distance_km: float, speed_kmh: float = 20.0) -> float:
    if not isfinite(distance_km) or distance_km < 0.0:
        raise ValueError("distance must be finite and non-negative")
    if not isfinite(speed_kmh) or speed_kmh <= 0.0:
        raise ValueError("speed must be positive and finite")
    return distance_km / speed_kmh * 60.0
