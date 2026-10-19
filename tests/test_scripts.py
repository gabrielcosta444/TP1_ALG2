import csv
from pathlib import Path
from types import SimpleNamespace

import scripts.benchmark_queries as benchmark_queries
from scripts.benchmark_queries import build_parser as build_benchmark_parser
from scripts.generate_couriers import build_parser as build_generation_parser
from scripts.prepare_restaurants import (
    build_parser as build_preparation_parser,
    main as prepare_main,
)

FIXTURE = Path(__file__).parent / "fixtures" / "atividade_economica_sample.csv"


def test_prepare_parser_accepts_source_and_destination() -> None:
    arguments = build_preparation_parser().parse_args(["source.csv", "output.csv"])

    assert arguments.source == Path("source.csv")
    assert arguments.destination == Path("output.csv")


def test_generate_parser_accepts_reproducible_generation_arguments() -> None:
    arguments = build_generation_parser().parse_args(
        [
            "restaurants.csv",
            "streets.graphml",
            "100",
            "couriers.csv",
            "--seed",
            "42",
            "--standard-deviation-m",
            "500",
        ]
    )

    assert arguments.restaurants == Path("restaurants.csv")
    assert arguments.street_cache == Path("streets.graphml")
    assert arguments.count == 100
    assert arguments.output == Path("couriers.csv")
    assert arguments.seed == 42
    assert arguments.standard_deviation_m == 500.0


def test_benchmark_parser_accepts_radii_and_output() -> None:
    arguments = build_benchmark_parser().parse_args(
        [
            "restaurants.csv",
            "streets.graphml",
            "100",
            "benchmark.csv",
            "--seed",
            "7",
            "--radii",
            "0.5",
            "2",
            "5",
        ]
    )

    assert arguments.restaurants == Path("restaurants.csv")
    assert arguments.street_cache == Path("streets.graphml")
    assert arguments.count == 100
    assert arguments.output == Path("benchmark.csv")
    assert arguments.seed == 7
    assert arguments.radii == [0.5, 2.0, 5.0]


def test_prepare_main_creates_processed_csv(tmp_path: Path) -> None:
    destination = tmp_path / "restaurants.csv"

    exit_code = prepare_main([str(FIXTURE), str(destination)])

    assert exit_code == 0
    with destination.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["id"] for row in rows] == ["r1", "r2"]


def test_benchmark_main_records_reproducibility_parameters(
    tmp_path: Path, monkeypatch
) -> None:
    output = tmp_path / "benchmark.csv"
    restaurant = SimpleNamespace(id="r1")

    class FakeRepository:
        def all(self):
            return (restaurant,)

    class FakeService:
        def __init__(self, repository, generator) -> None:
            pass

        def generate_couriers(self, count, seed, standard_deviation_m) -> None:
            assert (count, seed, standard_deviation_m) == (100, 7, 500.0)

        def search_nearby(self, restaurant_id, radius_km):
            assert (restaurant_id, radius_km) == ("r1", 2.0)
            return SimpleNamespace(
                metrics=SimpleNamespace(
                    prefix_length=5,
                    prefixes_visited=9,
                    candidates=12,
                    matches=3,
                    elapsed_ms=0.25,
                )
            )

    monkeypatch.setattr(
        benchmark_queries.RestaurantRepository,
        "from_csv",
        lambda path: FakeRepository(),
    )
    monkeypatch.setattr(
        benchmark_queries.OsmnxStreetSnapper,
        "from_place",
        lambda path: object(),
    )
    monkeypatch.setattr(
        benchmark_queries,
        "CourierGenerator",
        lambda restaurants, snapper: object(),
    )
    monkeypatch.setattr(benchmark_queries, "FleetService", FakeService)

    exit_code = benchmark_queries.main(
        [
            "restaurants.csv",
            "streets.graphml",
            "100",
            str(output),
            "--seed",
            "7",
            "--standard-deviation-m",
            "500",
            "--radii",
            "2",
        ]
    )

    assert exit_code == 0
    with output.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row == {
        "seed": "7",
        "courier_count": "100",
        "standard_deviation_m": "500.0",
        "restaurant_id": "r1",
        "radius_km": "2.0",
        "prefix_length": "5",
        "prefixes_visited": "9",
        "candidates": "12",
        "matches": "3",
        "elapsed_ms": "0.250000",
    }
