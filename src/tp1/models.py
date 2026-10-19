
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinate:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180 degrees")


@dataclass(frozen=True, slots=True)
class Restaurant:
    id: str
    name: str
    address: str
    neighborhood: str
    coordinate: Coordinate


@dataclass(frozen=True, slots=True)
class Courier:
    id: str
    coordinate: Coordinate
    geohash: str


@dataclass(frozen=True, slots=True)
class CourierMatch:
    courier: Courier
    distance_km: float
    eta_minutes: float


@dataclass(frozen=True, slots=True)
class SearchMetrics:
    prefix_length: int
    prefixes_visited: int
    candidates: int
    matches: int
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    restaurant: Restaurant
    matches: tuple[CourierMatch, ...]
    rejected_ids: tuple[str, ...]
    metrics: SearchMetrics
