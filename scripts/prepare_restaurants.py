
import argparse
from pathlib import Path
from typing import Sequence

from tp1.restaurants import prepare_restaurants


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara a base de restaurantes a partir do CSV da PBH."
    )
    parser.add_argument("source", type=Path, help="CSV original da PBH")
    parser.add_argument("destination", type=Path, help="CSV processado de saída")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    stats = prepare_restaurants(arguments.source, arguments.destination)
    print(
        f"Processadas {stats.total_rows} linhas: "
        f"{stats.written_rows} restaurantes gravados, "
        f"{stats.filtered_rows} atividades filtradas, "
        f"{stats.invalid_rows} linhas inválidas e "
        f"{stats.duplicate_rows} duplicatas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

