from math import degrees

import pytest

from tp1.geohash import encode, precision_for_radius, prefixes_for_radius
from tp1.models import Coordinate, Courier, Restaurant
from tp1.restaurants import RestaurantRepository
from tp1.service import FleetService


class QueueGenerator:
    def __init__(self, *responses: tuple[Courier, ...] | Exception) -> None:
        self._responses = list(responses)

    def generate(
        self,
        count: int,
        seed: int | None = None,
        standard_deviation_m: float = 800.0,
    ) -> tuple[Courier, ...]:
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _restaurant() -> Restaurant:
    return Restaurant(
        "r1",
        "Restaurante Central",
        "Rua Principal, 10",
        "Centro",
        Coordinate(-19.92, -43.94),
    )


def _courier(identifier: str, coordinate: Coordinate) -> Courier:
    return Courier(identifier, coordinate, encode(coordinate, precision=8))


def _service_with_responses(
    *responses: tuple[Courier, ...] | Exception,
) -> FleetService:
    repository = RestaurantRepository((_restaurant(),))
    return FleetService(repository, QueueGenerator(*responses))


def test_second_generation_replaces_fleet_and_index_completely() -> None:
    center = _restaurant().coordinate
    old = _courier("old", center)
    new = _courier("new", Coordinate(center.latitude + 0.001, center.longitude))
    service = _service_with_responses((old,), (new,))

    service.generate_couriers(1)
    generated = service.generate_couriers(1)
    result = service.search_nearby("r1", radius_km=2.0)

    assert generated == (new,)
    assert service.couriers == (new,)
    assert [match.courier.id for match in result.matches] == ["new"]
    assert "old" not in result.rejected_ids


def test_failed_generation_preserves_previous_fleet_and_index() -> None:
    current = _courier("current", _restaurant().coordinate)
    service = _service_with_responses(
        (current,), RuntimeError("street graph unavailable")
    )
    service.generate_couriers(1)

    with pytest.raises(RuntimeError, match="street graph unavailable"):
        service.generate_couriers(2)

    assert service.couriers == (current,)
    assert [
        match.courier.id
        for match in service.search_nearby("r1", radius_km=2.0).matches
    ] == ["current"]


def test_search_uses_neighbor_prefix_filters_radius_and_sorts_matches() -> None:
    center = _restaurant().coordinate
    half_km_latitude = degrees(0.5 / 6371.0088)
    two_km_latitude = degrees(2.0 / 6371.0088)
    three_km_latitude = degrees(3.0 / 6371.0088)
    same_distance_b = _courier(
        "b", Coordinate(center.latitude + half_km_latitude, center.longitude)
    )
    same_distance_a = _courier(
        "a", Coordinate(center.latitude - half_km_latitude, center.longitude)
    )
    neighbor = _courier("neighbor", Coordinate(center.latitude, -43.949))
    boundary = _courier(
        "boundary", Coordinate(center.latitude + two_km_latitude, center.longitude)
    )
    outside = _courier(
        "outside", Coordinate(center.latitude + three_km_latitude, center.longitude)
    )
    precision = precision_for_radius(center, 2.0)
    assert encode(neighbor.coordinate, precision) != encode(center, precision)
    assert encode(neighbor.coordinate, precision) in prefixes_for_radius(center, 2.0)

    service = _service_with_responses(
        (same_distance_b, same_distance_a, neighbor, boundary, outside)
    )
    service.generate_couriers(5)

    result = service.search_nearby("r1", radius_km=2.0)

    assert [match.courier.id for match in result.matches] == [
        "a",
        "b",
        "neighbor",
        "boundary",
    ]
    assert result.matches[0].eta_minutes == pytest.approx(1.5, abs=0.001)
    assert result.rejected_ids == ("outside",)
    assert result.metrics.prefix_length == 5
    assert result.metrics.prefixes_visited == 9
    assert result.metrics.candidates == 5
    assert result.metrics.matches == 4
    assert result.metrics.elapsed_ms >= 0.0


def test_search_restaurants_delegates_to_repository() -> None:
    service = _service_with_responses(())

    assert service.search_restaurants("central", limit=1)[0].id == "r1"


def test_search_without_generated_fleet_raises_runtime_error() -> None:
    service = _service_with_responses(())

    with pytest.raises(RuntimeError, match="fleet"):
        service.search_nearby("r1", radius_km=2.0)


def test_search_for_missing_restaurant_raises_lookup_error() -> None:
    courier = _courier("c1", _restaurant().coordinate)
    service = _service_with_responses((courier,))
    service.generate_couriers(1)

    with pytest.raises(LookupError):
        service.search_nearby("missing", radius_km=2.0)


@pytest.mark.parametrize(
    "radius_km, speed_kmh",
    [(0.0, 20.0), (-1.0, 20.0), (20.1, 20.0), (2.0, 0.0)],
)
def test_search_rejects_invalid_radius_or_speed(
    radius_km: float, speed_kmh: float
) -> None:
    courier = _courier("c1", _restaurant().coordinate)
    service = _service_with_responses((courier,))
    service.generate_couriers(1)

    with pytest.raises(ValueError):
        service.search_nearby("r1", radius_km, speed_kmh)


def test_valid_search_without_matches_returns_empty_result() -> None:
    center = _restaurant().coordinate
    far = _courier("far", Coordinate(center.latitude + 0.05, center.longitude))
    service = _service_with_responses((far,))
    service.generate_couriers(1)

    result = service.search_nearby("r1", radius_km=0.1)

    assert result.matches == ()
    assert result.rejected_ids == ("far",)
    assert result.metrics.matches == 0
