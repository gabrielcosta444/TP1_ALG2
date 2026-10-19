
from math import isfinite
from pathlib import Path
from random import Random
from typing import Protocol, Sequence

import osmnx as ox
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point

from tp1.geohash import encode
from tp1.models import Coordinate, Courier, Restaurant

_WGS84 = "EPSG:4326"
_PBH_PROJECTED = "EPSG:31983"


class StreetSnapper(Protocol):
    def snap_all(
        self, coordinates: Sequence[Coordinate]
    ) -> tuple[Coordinate, ...]: ...


def project_point_to_line(point: Point, line: LineString) -> Point:
    return line.interpolate(line.project(point))


class OsmnxStreetSnapper:

    def __init__(self, graph: object) -> None:
        graph_crs = CRS.from_user_input(graph.graph["crs"])
        if not graph_crs.equals(CRS.from_epsg(31983)):
            graph = ox.project_graph(graph, to_crs=_PBH_PROJECTED)
        self._graph = graph
        self._to_projected = Transformer.from_crs(
            _WGS84, _PBH_PROJECTED, always_xy=True
        )
        self._to_wgs84 = Transformer.from_crs(
            _PBH_PROJECTED, _WGS84, always_xy=True
        )

    @classmethod
    def from_place(
        cls,
        cache_path: Path,
        place: str = "Belo Horizonte, Minas Gerais, Brazil",
    ) -> "OsmnxStreetSnapper":
        try:
            if cache_path.exists():
                graph = ox.load_graphml(cache_path)
            else:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                graph = ox.graph_from_place(
                    place, network_type="drive", simplify=True
                )
                graph = ox.project_graph(graph, to_crs=_PBH_PROJECTED)
                ox.save_graphml(graph, filepath=cache_path)
            return cls(graph)
        except Exception as error:
            raise RuntimeError(
                f"unable to load or download street network: {error}"
            ) from error

    def snap_all(
        self, coordinates: Sequence[Coordinate]
    ) -> tuple[Coordinate, ...]:
        if not coordinates:
            return ()

        longitudes = [coordinate.longitude for coordinate in coordinates]
        latitudes = [coordinate.latitude for coordinate in coordinates]
        x_values, y_values = self._to_projected.transform(longitudes, latitudes)
        edge_ids = ox.distance.nearest_edges(
            self._graph,
            X=list(x_values),
            Y=list(y_values),
        )

        snapped: list[Coordinate] = []
        for x, y, edge_id in zip(x_values, y_values, edge_ids, strict=True):
            u, v, key = edge_id
            data = self._graph.get_edge_data(u, v, key)
            line = data.get("geometry")
            if line is None:
                start = self._graph.nodes[u]
                end = self._graph.nodes[v]
                line = LineString(
                    [(start["x"], start["y"]), (end["x"], end["y"])]
                )
            projected = project_point_to_line(Point(x, y), line)
            longitude, latitude = self._to_wgs84.transform(projected.x, projected.y)
            snapped.append(Coordinate(latitude, longitude))
        return tuple(snapped)


class CourierGenerator:
    def __init__(
        self, restaurants: Sequence[Restaurant], snapper: StreetSnapper
    ) -> None:
        self._restaurants = tuple(restaurants)
        self._snapper = snapper
        self._to_projected = Transformer.from_crs(
            _WGS84, _PBH_PROJECTED, always_xy=True
        )
        self._to_wgs84 = Transformer.from_crs(
            _PBH_PROJECTED, _WGS84, always_xy=True
        )

    def generate(
        self,
        count: int,
        seed: int | None = None,
        standard_deviation_m: float = 800.0,
    ) -> tuple[Courier, ...]:
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10_000:
            raise ValueError("count must be an integer between 1 and 10000")
        if not isfinite(standard_deviation_m) or standard_deviation_m < 0.0:
            raise ValueError("standard_deviation_m must be finite and non-negative")
        if not self._restaurants:
            raise ValueError("at least one restaurant is required")

        random = Random(seed)
        restaurant_count = len(self._restaurants)
        base_count, remainder = divmod(count, restaurant_count)
        counts = [base_count] * restaurant_count
        remainder_order = list(range(restaurant_count))
        random.shuffle(remainder_order)
        for index in remainder_order[:remainder]:
            counts[index] += 1

        generated: list[Coordinate] = []
        for restaurant, amount in zip(self._restaurants, counts, strict=True):
            center_x, center_y = self._to_projected.transform(
                restaurant.coordinate.longitude,
                restaurant.coordinate.latitude,
            )
            for _ in range(amount):
                x = center_x + random.gauss(0.0, standard_deviation_m)
                y = center_y + random.gauss(0.0, standard_deviation_m)
                longitude, latitude = self._to_wgs84.transform(x, y)
                generated.append(Coordinate(latitude, longitude))

        snapped = self._snapper.snap_all(tuple(generated))
        if len(snapped) != count:
            raise RuntimeError("street snapper returned an unexpected point count")

        return tuple(
            Courier(
                id=f"courier-{index:06d}",
                coordinate=coordinate,
                geohash=encode(coordinate, precision=8),
            )
            for index, coordinate in enumerate(snapped, start=1)
        )
