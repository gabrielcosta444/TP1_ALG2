
from dataclasses import dataclass
from math import isfinite, nextafter

from tp1.geometry import haversine_km
from tp1.models import Coordinate

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {character: index for index, character in enumerate(BASE32)}
_NEIGHBOR_OFFSETS = (
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
    (1, -1),
)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    south: float
    west: float
    north: float
    east: float

    @property
    def center(self) -> Coordinate:
        return Coordinate(
            latitude=(self.south + self.north) / 2.0,
            longitude=(self.west + self.east) / 2.0,
        )


def encode(coordinate: Coordinate, precision: int = 8) -> str:
    _validate_precision(precision)
    latitude_interval = [-90.0, 90.0]
    longitude_interval = [-180.0, 180.0]
    characters: list[str] = []
    current_value = 0
    bits_in_character = 0
    use_longitude = True

    while len(characters) < precision:
        interval = longitude_interval if use_longitude else latitude_interval
        value = coordinate.longitude if use_longitude else coordinate.latitude
        midpoint = (interval[0] + interval[1]) / 2.0
        current_value <<= 1
        if value >= midpoint:
            current_value |= 1
            interval[0] = midpoint
        else:
            interval[1] = midpoint

        bits_in_character += 1
        use_longitude = not use_longitude
        if bits_in_character == 5:
            characters.append(BASE32[current_value])
            current_value = 0
            bits_in_character = 0

    return "".join(characters)


def decode_bbox(value: str) -> BoundingBox:
    if not value or len(value) > 8:
        raise ValueError("geohash length must be between 1 and 8")
    if any(character not in _DECODE for character in value):
        raise ValueError("geohash contains an invalid Base32 character")

    latitude_interval = [-90.0, 90.0]
    longitude_interval = [-180.0, 180.0]
    use_longitude = True

    for character in value:
        encoded = _DECODE[character]
        for mask in (16, 8, 4, 2, 1):
            interval = longitude_interval if use_longitude else latitude_interval
            midpoint = (interval[0] + interval[1]) / 2.0
            if encoded & mask:
                interval[0] = midpoint
            else:
                interval[1] = midpoint
            use_longitude = not use_longitude

    return BoundingBox(
        south=latitude_interval[0],
        west=longitude_interval[0],
        north=latitude_interval[1],
        east=longitude_interval[1],
    )


def neighbors(value: str) -> tuple[str, ...]:
    bbox = decode_bbox(value)
    center = bbox.center
    latitude_step = bbox.north - bbox.south
    longitude_step = bbox.east - bbox.west
    adjacent: list[str] = []

    for latitude_offset, longitude_offset in _NEIGHBOR_OFFSETS:
        latitude = center.latitude + latitude_offset * latitude_step
        longitude = center.longitude + longitude_offset * longitude_step
        latitude = min(nextafter(90.0, 0.0), max(nextafter(-90.0, 0.0), latitude))
        longitude = _normalize_longitude(longitude)
        adjacent.append(encode(Coordinate(latitude, longitude), len(value)))

    return tuple(adjacent)


def cell_dimensions_km(value: str) -> tuple[float, float]:
    bbox = decode_bbox(value)
    center = bbox.center
    height = haversine_km(
        Coordinate(bbox.south, center.longitude),
        Coordinate(bbox.north, center.longitude),
    )
    width = haversine_km(
        Coordinate(center.latitude, bbox.west),
        Coordinate(center.latitude, bbox.east),
    )
    return height, width


def precision_for_radius(
    coordinate: Coordinate, radius_km: float, max_precision: int = 8
) -> int:
    if not isfinite(radius_km) or radius_km <= 0.0:
        raise ValueError("radius must be a positive finite number")
    _validate_precision(max_precision)

    selected = 1
    for precision in range(1, max_precision + 1):
        height, width = cell_dimensions_km(encode(coordinate, precision))
        if height >= radius_km and width >= radius_km:
            selected = precision
        else:
            break
    return selected


def prefixes_for_radius(
    coordinate: Coordinate, radius_km: float, max_precision: int = 8
) -> tuple[str, ...]:
    precision = precision_for_radius(coordinate, radius_km, max_precision)
    center = encode(coordinate, precision)
    return (center, *neighbors(center))


def _validate_precision(precision: int) -> None:
    if not isinstance(precision, int) or isinstance(precision, bool):
        raise ValueError("precision must be an integer between 1 and 8")
    if not 1 <= precision <= 8:
        raise ValueError("precision must be between 1 and 8")


def _normalize_longitude(longitude: float) -> float:
    normalized = (longitude + 180.0) % 360.0 - 180.0
    return 0.0 if normalized == -0.0 else normalized
