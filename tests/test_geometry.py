import pytest

from tp1.geometry import estimate_eta_minutes, haversine_km
from tp1.models import Coordinate


def test_haversine_returns_zero_for_same_coordinate() -> None:
    point = Coordinate(-19.9227, -43.9451)

    assert haversine_km(point, point) == pytest.approx(0.0)


def test_haversine_is_symmetric_and_matches_one_degree_at_equator() -> None:
    origin = Coordinate(0.0, 0.0)
    destination = Coordinate(1.0, 0.0)

    forward = haversine_km(origin, destination)
    backward = haversine_km(destination, origin)

    assert forward == pytest.approx(111.195, abs=0.001)
    assert backward == pytest.approx(forward)


def test_eta_uses_configured_average_speed() -> None:
    assert estimate_eta_minutes(10.0, 20.0) == pytest.approx(30.0)


@pytest.mark.parametrize(
    "distance_km, speed_kmh",
    [
        (-1.0, 20.0),
        (1.0, 0.0),
        (1.0, -20.0),
        (float("nan"), 20.0),
        (float("inf"), 20.0),
        (1.0, float("nan")),
        (1.0, float("inf")),
    ],
)
def test_eta_rejects_invalid_distance_or_speed(
    distance_km: float, speed_kmh: float
) -> None:
    with pytest.raises(ValueError):
        estimate_eta_minutes(distance_km, speed_kmh)
