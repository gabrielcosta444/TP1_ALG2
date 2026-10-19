import csv
import re
from pathlib import Path

import pytest

from tp1.models import Coordinate
from tp1.restaurants import (
    PbhCoordinateTransformer,
    RestaurantRepository,
    prepare_restaurants,
)

FIXTURE = Path(__file__).parent / "fixtures" / "atividade_economica_sample.csv"


class FakeCoordinateTransformer:
    def transform_wkt(self, value: str) -> Coordinate:
        match = re.fullmatch(r"POINT \((\d+) (\d+)\)", value)
        if match is None:
            raise ValueError("invalid point")
        x, y = (float(part) for part in match.groups())
        return Coordinate((y - 8_000_000.0) / 10_000.0, (x - 1_000_000.0) / 10_000.0)


def test_prepare_restaurants_filters_transforms_and_counts_rows(tmp_path: Path) -> None:
    destination = tmp_path / "restaurants.csv"

    stats = prepare_restaurants(FIXTURE, destination, FakeCoordinateTransformer())

    assert stats.total_rows == 5
    assert stats.written_rows == 2
    assert stats.filtered_rows == 1
    assert stats.invalid_rows == 1
    assert stats.duplicate_rows == 1

    with destination.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert list(rows[0]) == [
        "id",
        "name",
        "address",
        "neighborhood",
        "latitude",
        "longitude",
    ]
    assert [row["id"] for row in rows] == ["r1", "r2"]
    assert rows[0]["name"] == "Açaí do Centro"
    assert rows[0]["address"] == "AVENIDA AFONSO PENA, 1000 - LOJA 1"
    assert rows[1]["name"] == "Bar do João Ltda"


def test_pbh_transformer_converts_epsg_31983_point_to_belo_horizonte() -> None:
    coordinate = PbhCoordinateTransformer().transform_wkt(
        "POINT (611748.06 7798276.46)"
    )

    assert -20.0 < coordinate.latitude < -19.8
    assert -44.1 < coordinate.longitude < -43.8


def test_repository_loads_in_file_order_and_gets_by_id(tmp_path: Path) -> None:
    destination = tmp_path / "restaurants.csv"
    prepare_restaurants(FIXTURE, destination, FakeCoordinateTransformer())

    repository = RestaurantRepository.from_csv(destination)

    assert [restaurant.id for restaurant in repository.all()] == ["r1", "r2"]
    assert repository.get("r2").name == "Bar do João Ltda"
    with pytest.raises(LookupError):
        repository.get("missing")


@pytest.mark.parametrize(
    "query, expected_id",
    [("acai", "r1"), ("sapucai", "r2"), ("floresta", "r2")],
)
def test_repository_search_ignores_case_and_accents(
    tmp_path: Path, query: str, expected_id: str
) -> None:
    destination = tmp_path / "restaurants.csv"
    prepare_restaurants(FIXTURE, destination, FakeCoordinateTransformer())
    repository = RestaurantRepository.from_csv(destination)

    assert repository.search(query)[0].id == expected_id


def test_repository_search_sorts_results_and_applies_limit(tmp_path: Path) -> None:
    destination = tmp_path / "restaurants.csv"
    prepare_restaurants(FIXTURE, destination, FakeCoordinateTransformer())
    repository = RestaurantRepository.from_csv(destination)

    assert [item.id for item in repository.search("", limit=1)] == ["r1"]
    with pytest.raises(ValueError):
        repository.search("", limit=0)
