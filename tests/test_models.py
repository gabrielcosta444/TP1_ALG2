from dataclasses import FrozenInstanceError

from importlib.util import find_spec

import pytest

from tp1.models import (
    Coordinate,
    Courier,
    CourierMatch,
    Restaurant,
    SearchMetrics,
    SearchResult,
)


def test_project_domain_is_available_from_neutral_tp1_package() -> None:
    assert find_spec("tp1") is not None


def test_models_are_immutable_value_objects() -> None:
    coordinate = Coordinate(-19.9227, -43.9451)
    restaurant = Restaurant(
        id="r1",
        name="Restaurante Teste",
        address="Rua Teste, 10",
        neighborhood="Centro",
        coordinate=coordinate,
    )
    courier = Courier(id="c1", coordinate=coordinate, geohash="7h2x4abc")
    match = CourierMatch(courier=courier, distance_km=1.0, eta_minutes=3.0)
    metrics = SearchMetrics(5, 9, 1, 1, 0.5)

    assert restaurant == Restaurant(
        "r1", "Restaurante Teste", "Rua Teste, 10", "Centro", coordinate
    )
    assert match == CourierMatch(courier, 1.0, 3.0)
    assert metrics == SearchMetrics(5, 9, 1, 1, 0.5)

    with pytest.raises(FrozenInstanceError):
        coordinate.latitude = 0


def test_search_result_uses_tuples() -> None:
    coordinate = Coordinate(-19.9227, -43.9451)
    restaurant = Restaurant("r1", "Teste", "Rua A", "Centro", coordinate)
    courier = Courier("c1", coordinate, "7h2x4abc")
    match = CourierMatch(courier, 1.0, 3.0)
    metrics = SearchMetrics(5, 9, 1, 1, 0.5)

    result = SearchResult(restaurant, (match,), ("c2",), metrics)

    assert result.matches == (match,)
    assert result.rejected_ids == ("c2",)


@pytest.mark.parametrize(
    "latitude, longitude",
    [
        (91.0, 0.0),
        (-91.0, 0.0),
        (0.0, 181.0),
        (0.0, -181.0),
        (float("nan"), 0.0),
        (0.0, float("nan")),
        (float("inf"), 0.0),
        (0.0, float("-inf")),
    ],
)
def test_coordinate_rejects_out_of_range_values(
    latitude: float, longitude: float
) -> None:
    with pytest.raises(ValueError):
        Coordinate(latitude, longitude)
