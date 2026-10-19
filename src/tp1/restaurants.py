
import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pyproj import Transformer

from tp1.models import Coordinate, Restaurant

_OUTPUT_FIELDS = (
    "id",
    "name",
    "address",
    "neighborhood",
    "latitude",
    "longitude",
)
_POINT_PATTERN = re.compile(
    r"^\s*POINT\s*\(\s*"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s+"
    r"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"\s*\)\s*$",
    re.IGNORECASE,
)


class CoordinateTransformer(Protocol):
    def transform_wkt(self, value: str) -> Coordinate: ...


@dataclass(frozen=True, slots=True)
class PreparationStats:
    total_rows: int
    written_rows: int
    filtered_rows: int
    invalid_rows: int
    duplicate_rows: int


class PbhCoordinateTransformer:

    def __init__(self) -> None:
        self._transformer = Transformer.from_crs(
            "EPSG:31983", "EPSG:4326", always_xy=True
        )

    def transform_wkt(self, value: str) -> Coordinate:
        match = _POINT_PATTERN.fullmatch(value or "")
        if match is None:
            raise ValueError("geometry must be a WKT POINT")
        x, y = (float(part) for part in match.groups())
        longitude, latitude = self._transformer.transform(x, y)
        return Coordinate(latitude=latitude, longitude=longitude)


def prepare_restaurants(
    source: Path,
    destination: Path,
    transformer: CoordinateTransformer | None = None,
) -> PreparationStats:
    coordinate_transformer = transformer or PbhCoordinateTransformer()
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_rows = written_rows = filtered_rows = invalid_rows = duplicate_rows = 0
    seen_ids: set[str] = set()

    with source.open(encoding="utf-8-sig", newline="") as source_stream:
        sample = source_stream.read(8192)
        source_stream.seek(0)
        delimiter = _detect_delimiter(sample)
        reader = csv.DictReader(source_stream, delimiter=delimiter)

        with destination.open("w", encoding="utf-8", newline="") as output_stream:
            writer = csv.DictWriter(output_stream, fieldnames=_OUTPUT_FIELDS)
            writer.writeheader()

            for row in reader:
                total_rows += 1
                if not _is_restaurant_activity(row):
                    filtered_rows += 1
                    continue

                identifier = (row.get("ID_ATIV_ECON_ESTABELECIMENTO") or "").strip()
                if not identifier:
                    invalid_rows += 1
                    continue
                if identifier in seen_ids:
                    duplicate_rows += 1
                    continue

                try:
                    coordinate = coordinate_transformer.transform_wkt(
                        (row.get("GEOMETRIA") or "").strip()
                    )
                except (TypeError, ValueError):
                    invalid_rows += 1
                    continue

                name = (
                    (row.get("NOME_FANTASIA") or "").strip()
                    or (row.get("NOME") or "").strip()
                    or identifier
                )
                seen_ids.add(identifier)
                writer.writerow(
                    {
                        "id": identifier,
                        "name": name,
                        "address": _build_address(row),
                        "neighborhood": (row.get("NOME_BAIRRO") or "").strip(),
                        "latitude": f"{coordinate.latitude:.8f}",
                        "longitude": f"{coordinate.longitude:.8f}",
                    }
                )
                written_rows += 1

    return PreparationStats(
        total_rows=total_rows,
        written_rows=written_rows,
        filtered_rows=filtered_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
    )


class RestaurantRepository:
    def __init__(self, restaurants: tuple[Restaurant, ...]) -> None:
        self._restaurants = restaurants
        self._by_id = {restaurant.id: restaurant for restaurant in restaurants}
        self._searchable = {
            restaurant.id: _normalize_text(
                " ".join(
                    (restaurant.name, restaurant.address, restaurant.neighborhood)
                )
            )
            for restaurant in restaurants
        }

    @classmethod
    def from_csv(cls, path: Path) -> "RestaurantRepository":
        restaurants: list[Restaurant] = []
        seen_ids: set[str] = set()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            for row in reader:
                identifier = (row.get("id") or "").strip()
                if not identifier or identifier in seen_ids:
                    continue
                coordinate = Coordinate(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                )
                restaurants.append(
                    Restaurant(
                        id=identifier,
                        name=(row.get("name") or identifier).strip(),
                        address=(row.get("address") or "").strip(),
                        neighborhood=(row.get("neighborhood") or "").strip(),
                        coordinate=coordinate,
                    )
                )
                seen_ids.add(identifier)
        return cls(tuple(restaurants))

    def all(self) -> tuple[Restaurant, ...]:
        return self._restaurants

    def get(self, restaurant_id: str) -> Restaurant:
        try:
            return self._by_id[restaurant_id]
        except KeyError as error:
            raise LookupError(f"restaurant not found: {restaurant_id}") from error

    def search(self, text: str, limit: int = 20) -> tuple[Restaurant, ...]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        query = _normalize_text(text)
        matches = (
            restaurant
            for restaurant in self._restaurants
            if query in self._searchable[restaurant.id]
        )
        ordered = sorted(matches, key=lambda item: (_normalize_text(item.name), item.id))
        return tuple(ordered[:limit])


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,",).delimiter
    except csv.Error:
        return ";" if sample.count(";") > sample.count(",") else ","


def _is_restaurant_activity(row: dict[str, str | None]) -> bool:
    values = (
        row.get("CNAE_PRINCIPAL") or "",
        row.get("CNAE") or "",
    )
    for value in values:
        for code in re.split(r"[,;|]", value):
            normalized = re.sub(r"\D", "", code)
            if normalized.startswith("56112"):
                return True
    return False


def _build_address(row: dict[str, str | None]) -> str:
    street = " ".join(
        part
        for part in (
            (row.get("DESC_LOGRADOURO") or "").strip(),
            (row.get("NOME_LOGRADOURO") or "").strip(),
        )
        if part
    )
    number = (row.get("NUMERO_IMOVEL") or "").strip()
    complement = (row.get("COMPLEMENTO") or "").strip().rstrip(",")
    address = f"{street}, {number}" if street and number else street or number
    return f"{address} - {complement}" if address and complement else address or complement


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))
