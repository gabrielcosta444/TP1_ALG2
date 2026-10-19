
import argparse
import csv
from pathlib import Path
from typing import Sequence

from tp1.restaurants import RestaurantRepository
from tp1.simulation import CourierGenerator, OsmnxStreetSnapper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera uma frota reproduzível e exporta os dados em CSV."
    )
    parser.add_argument("restaurants", type=Path, help="CSV de restaurantes processado")
    parser.add_argument("street_cache", type=Path, help="cache GraphML da malha viária")
    parser.add_argument("count", type=int, help="quantidade de entregadores")
    parser.add_argument("output", type=Path, help="CSV de saída da frota")
    parser.add_argument("--seed", type=int, default=None, help="semente aleatória")
    parser.add_argument(
        "--standard-deviation-m",
        type=float,
        default=800.0,
        help="desvio padrão espacial em metros",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    repository = RestaurantRepository.from_csv(arguments.restaurants)
    snapper = OsmnxStreetSnapper.from_place(arguments.street_cache)
    generator = CourierGenerator(repository.all(), snapper)
    couriers = generator.generate(
        arguments.count,
        seed=arguments.seed,
        standard_deviation_m=arguments.standard_deviation_m,
    )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=("id", "latitude", "longitude", "geohash")
        )
        writer.writeheader()
        for courier in couriers:
            writer.writerow(
                {
                    "id": courier.id,
                    "latitude": f"{courier.coordinate.latitude:.8f}",
                    "longitude": f"{courier.coordinate.longitude:.8f}",
                    "geohash": courier.geohash,
                }
            )
    print(f"{len(couriers)} entregadores gravados em {arguments.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

