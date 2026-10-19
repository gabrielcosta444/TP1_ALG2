import pytest

from tp1.geohash import (
    decode_bbox,
    encode,
    neighbors,
    precision_for_radius,
    prefixes_for_radius,
)
from tp1.models import Coordinate


def test_encode_matches_canonical_geohash_example() -> None:
    assert encode(Coordinate(42.6, -5.6), precision=5) == "ezs42"


def test_decoded_bbox_contains_original_coordinate() -> None:
    point = Coordinate(-19.9227, -43.9451)

    bbox = decode_bbox(encode(point, precision=8))

    assert bbox.south <= point.latitude <= bbox.north
    assert bbox.west <= point.longitude <= bbox.east


@pytest.mark.parametrize("precision", [0, 9])
def test_encode_rejects_precision_outside_supported_range(precision: int) -> None:
    with pytest.raises(ValueError):
        encode(Coordinate(0.0, 0.0), precision)


@pytest.mark.parametrize("value", ["", "ezs4a", "EZS42"])
def test_decode_rejects_empty_or_invalid_geohash(value: str) -> None:
    with pytest.raises(ValueError):
        decode_bbox(value)


def test_neighbors_returns_eight_distinct_adjacent_cells() -> None:
    center = encode(Coordinate(-19.9227, -43.9451), precision=5)

    adjacent = neighbors(center)

    assert len(adjacent) == 8
    assert len(set(adjacent)) == 8
    assert center not in adjacent
    assert all(len(value) == 5 for value in adjacent)


@pytest.mark.parametrize(
    "point",
    [Coordinate(0.0, 179.999), Coordinate(89.999, 0.0)],
)
def test_neighbors_remain_valid_near_world_limits(point: Coordinate) -> None:
    adjacent = neighbors(encode(point, precision=5))

    assert len(adjacent) == 8
    for value in adjacent:
        bbox = decode_bbox(value)
        assert -90.0 <= bbox.south <= bbox.north <= 90.0
        assert -180.0 <= bbox.west <= bbox.east <= 180.0


def test_precision_for_radius_uses_largest_cell_that_covers_radius() -> None:
    point = Coordinate(-19.9227, -43.9451)

    assert precision_for_radius(point, 2.0) == 5
    assert precision_for_radius(point, 0.5) == 6


def test_prefixes_for_radius_contains_center_and_eight_neighbors() -> None:
    point = Coordinate(-19.9227, -43.9451)

    prefixes = prefixes_for_radius(point, 2.0)

    assert len(prefixes) == 9
    assert len(set(prefixes)) == 9
    assert prefixes[0] == encode(point, precision=5)


@pytest.mark.parametrize("radius_km", [0.0, -1.0])
def test_precision_for_radius_rejects_non_positive_radius(radius_km: float) -> None:
    with pytest.raises(ValueError):
        precision_for_radius(Coordinate(0.0, 0.0), radius_km)
