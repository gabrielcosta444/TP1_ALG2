from collections import Counter
from pathlib import Path

import networkx as nx
import pytest
from pyproj import Transformer
from shapely.geometry import LineString, Point

from tp1.geometry import haversine_km
from tp1.models import Coordinate, Restaurant
import tp1.simulation as simulation
from tp1.simulation import (
    CourierGenerator,
    OsmnxStreetSnapper,
    project_point_to_line,
)


class IdentitySnapper:
    def snap_all(
        self, coordinates: tuple[Coordinate, ...]
    ) -> tuple[Coordinate, ...]:
        return tuple(coordinates)


class FailingSnapper:
    def snap_all(
        self, coordinates: tuple[Coordinate, ...]
    ) -> tuple[Coordinate, ...]:
        raise RuntimeError("street graph unavailable")


def _restaurants() -> tuple[Restaurant, ...]:
    return (
        Restaurant("r1", "Um", "Rua 1", "Centro", Coordinate(-19.92, -43.94)),
        Restaurant("r2", "Dois", "Rua 2", "Savassi", Coordinate(-19.94, -43.93)),
        Restaurant("r3", "Três", "Rua 3", "Pampulha", Coordinate(-19.85, -43.97)),
    )


def test_generator_distributes_exact_count_evenly_and_builds_ids() -> None:
    restaurants = _restaurants()
    generator = CourierGenerator(restaurants, IdentitySnapper())

    couriers = generator.generate(8, seed=7, standard_deviation_m=0.0)

    assert [courier.id for courier in couriers] == [
        f"courier-{index:06d}" for index in range(1, 9)
    ]
    assert all(len(courier.geohash) == 8 for courier in couriers)
    centers = Counter(
        min(
            restaurants,
            key=lambda restaurant: haversine_km(
                courier.coordinate, restaurant.coordinate
            ),
        ).id
        for courier in couriers
    )
    assert sorted(centers.values()) == [2, 3, 3]


def test_generator_handles_count_below_number_of_restaurants() -> None:
    couriers = CourierGenerator(_restaurants(), IdentitySnapper()).generate(
        2, seed=3, standard_deviation_m=0.0
    )

    assert len(couriers) == 2
    assert len({courier.coordinate for courier in couriers}) == 2


def test_generator_is_reproducible_for_same_seed() -> None:
    generator = CourierGenerator(_restaurants(), IdentitySnapper())

    first = generator.generate(5, seed=42, standard_deviation_m=250.0)
    second = generator.generate(5, seed=42, standard_deviation_m=250.0)

    assert first == second


@pytest.mark.parametrize(
    "count, standard_deviation_m",
    [(0, 800.0), (10_001, 800.0), (1, -1.0)],
)
def test_generator_rejects_invalid_count_or_deviation(
    count: int, standard_deviation_m: float
) -> None:
    generator = CourierGenerator(_restaurants(), IdentitySnapper())

    with pytest.raises(ValueError):
        generator.generate(count, standard_deviation_m=standard_deviation_m)


def test_generator_requires_at_least_one_restaurant() -> None:
    with pytest.raises(ValueError):
        CourierGenerator((), IdentitySnapper()).generate(1)


def test_generator_propagates_snapper_failure_without_partial_result() -> None:
    generator = CourierGenerator(_restaurants(), FailingSnapper())

    with pytest.raises(RuntimeError, match="street graph unavailable"):
        generator.generate(3, seed=1)


def test_project_point_to_line_uses_nearest_position_on_edge() -> None:
    projected = project_point_to_line(
        Point(5.0, 3.0), LineString([(0.0, 0.0), (10.0, 0.0)])
    )

    assert projected.equals(Point(5.0, 0.0))


def test_osmnx_snapper_projects_coordinate_onto_synthetic_edge() -> None:
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "EPSG:31983"
    graph.add_node(1, x=600_000.0, y=7_800_000.0)
    graph.add_node(2, x=610_000.0, y=7_800_000.0)
    graph.add_edge(
        1,
        2,
        key=0,
        geometry=LineString(
            [(600_000.0, 7_800_000.0), (610_000.0, 7_800_000.0)]
        ),
    )
    to_wgs84 = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)
    longitude, latitude = to_wgs84.transform(605_000.0, 7_803_000.0)
    snapper = OsmnxStreetSnapper(graph)

    snapped = snapper.snap_all((Coordinate(latitude, longitude),))[0]

    to_projected = Transformer.from_crs("EPSG:4326", "EPSG:31983", always_xy=True)
    x, y = to_projected.transform(snapped.longitude, snapped.latitude)
    assert x == pytest.approx(605_000.0, abs=0.01)
    assert y == pytest.approx(7_800_000.0, abs=0.01)


def test_osmnx_snapper_reports_external_network_failure_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_download(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(simulation.ox, "graph_from_place", fail_download)

    with pytest.raises(RuntimeError, match="street network"):
        OsmnxStreetSnapper.from_place(tmp_path / "streets.graphml")
