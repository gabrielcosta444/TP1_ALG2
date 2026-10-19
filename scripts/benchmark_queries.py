
import argparse
import csv
from pathlib import Path
from typing import Sequence

from tp1.restaurants import RestaurantRepository
from tp1.service import FleetService
from tp1.simulation import CourierGenerator, OsmnxStreetSnapper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa consultas reproduzíveis e grava métricas em CSV."
    )
    parser.add_argument("restaurants", type=Path, help="CSV de restaurantes processado")
    parser.add_argument("street_cache", type=Path, help="cache GraphML da malha viária")
    parser.add_argument("count", type=int, help="quantidade de entregadores")
    parser.add_argument("output", type=Path, help="CSV de saída das métricas")
    parser.add_argument("--seed", type=int, default=0, help="semente aleatória")
    parser.add_argument(
        "--standard-deviation-m", type=float, default=800.0, help="desvio em metros"
    )
    parser.add_argument(
        "--radii",
        type=float,
        nargs="+",
        default=[0.5, 1.0, 2.0, 5.0],
        help="raios consultados em quilômetros",
    )
    parser.add_argument(
        "--restaurant-id",
        default=None,
        help="ID consultado; por padrão usa o primeiro restaurante",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    repository = RestaurantRepository.from_csv(arguments.restaurants)
    restaurants = repository.all()
    if not restaurants:
        raise RuntimeError("the restaurant dataset is empty")

    snapper = OsmnxStreetSnapper.from_place(arguments.street_cache)
    generator = CourierGenerator(restaurants, snapper)
    service = FleetService(repository, generator)
    service.generate_couriers(
        arguments.count,
        seed=arguments.seed,
        standard_deviation_m=arguments.standard_deviation_m,
    )
    restaurant_id = arguments.restaurant_id or restaurants[0].id

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "seed",
                "courier_count",
                "standard_deviation_m",
                "restaurant_id",
                "radius_km",
                "prefix_length",
                "prefixes_visited",
                "candidates",
                "matches",
                "elapsed_ms",
            ),
        )
        writer.writeheader()
        for radius_km in arguments.radii:
            result = service.search_nearby(restaurant_id, radius_km)
            writer.writerow(
                {
                    "seed": arguments.seed,
                    "courier_count": arguments.count,
                    "standard_deviation_m": arguments.standard_deviation_m,
                    "restaurant_id": restaurant_id,
                    "radius_km": radius_km,
                    "prefix_length": result.metrics.prefix_length,
                    "prefixes_visited": result.metrics.prefixes_visited,
                    "candidates": result.metrics.candidates,
                    "matches": result.metrics.matches,
                    "elapsed_ms": f"{result.metrics.elapsed_ms:.6f}",
                }
            )
    print(f"Métricas gravadas em {arguments.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

