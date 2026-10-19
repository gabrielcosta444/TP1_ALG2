
from collections.abc import Sequence, Set
from dataclasses import dataclass

from tp1.models import Courier, Restaurant, SearchResult

_EMPTY_FEATURE_COLLECTION: dict[str, object] = {
    "type": "FeatureCollection",
    "features": [],
}
_BH_CENTER = [-19.9167, -43.9345]


@dataclass(frozen=True, slots=True)
class DashboardView:
    courier_data: dict[str, object]
    restaurant_data: dict[str, object]
    rows: list[dict[str, str | float]]
    metrics: dict[str, str]
    center: list[float]
    zoom: int
    message: str


def restaurant_options(
    restaurants: Sequence[Restaurant],
) -> list[dict[str, str]]:
    return [
        {
            "label": " — ".join(
                part
                for part in (
                    restaurant.name,
                    restaurant.neighborhood,
                    restaurant.address,
                )
                if part
            ),
            "value": restaurant.id,
        }
        for restaurant in restaurants
    ]


def courier_feature_collection(
    couriers: Sequence[Courier],
    matched_ids: Set[str] = frozenset(),
) -> dict[str, object]:
    features = []
    for courier in couriers:
        matched = courier.id in matched_ids
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        courier.coordinate.longitude,
                        courier.coordinate.latitude,
                    ],
                },
                "properties": {
                    "id": courier.id,
                    "category": "matched" if matched else "rejected",
                    "label": courier.id,
                    "color": "#dc2626" if matched else "#80868b",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def restaurant_feature_collection(
    restaurant: Restaurant | None,
) -> dict[str, object]:
    if restaurant is None:
        return {**_EMPTY_FEATURE_COLLECTION, "features": []}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        restaurant.coordinate.longitude,
                        restaurant.coordinate.latitude,
                    ],
                },
                "properties": {
                    "id": restaurant.id,
                    "category": "restaurant",
                    "label": restaurant.name,
                    "color": "#163a5f",
                },
            }
        ],
    }


def result_rows(result: SearchResult | None) -> list[dict[str, str | float]]:
    if result is None:
        return []
    return [
        {
            "id": match.courier.id,
            "distance_km": round(match.distance_km, 2),
            "eta_minutes": round(match.eta_minutes, 2),
        }
        for match in result.matches
    ]


def result_metrics(result: SearchResult | None) -> dict[str, str]:
    if result is None:
        return {
            "candidates": "—",
            "matches": "—",
            "prefix": "—",
            "elapsed": "—",
        }
    return {
        "candidates": str(result.metrics.candidates),
        "matches": str(result.metrics.matches),
        "prefix": str(result.metrics.prefix_length),
        "elapsed": f"{result.metrics.elapsed_ms:.3f} ms",
    }


def generation_view(couriers: Sequence[Courier]) -> DashboardView:
    count = len(couriers)
    noun = "entregador gerado" if count == 1 else "entregadores gerados"
    return DashboardView(
        courier_data=courier_feature_collection(couriers),
        restaurant_data=restaurant_feature_collection(None),
        rows=[],
        metrics=result_metrics(None),
        center=list(_BH_CENTER),
        zoom=12,
        message=f"{count} {noun}.",
    )


def search_view(
    result: SearchResult,
    couriers: Sequence[Courier],
    radius_km: float,
) -> DashboardView:
    matched_ids = {match.courier.id for match in result.matches}
    count = len(result.matches)
    noun = "entregador encontrado" if count == 1 else "entregadores encontrados"
    return DashboardView(
        courier_data=courier_feature_collection(couriers, matched_ids),
        restaurant_data=restaurant_feature_collection(result.restaurant),
        rows=result_rows(result),
        metrics=result_metrics(result),
        center=[
            result.restaurant.coordinate.latitude,
            result.restaurant.coordinate.longitude,
        ],
        zoom=zoom_for_radius(radius_km),
        message=f"{count} {noun}.",
    )


def zoom_for_radius(radius_km: float) -> int:
    if radius_km <= 0.5:
        return 15
    if radius_km <= 1.0:
        return 14
    if radius_km <= 2.0:
        return 13
    if radius_km <= 5.0:
        return 12
    if radius_km <= 10.0:
        return 11
    return 10


def error_message(error: Exception) -> str:
    if isinstance(error, ValueError):
        return "Parâmetro inválido. Revise os valores informados."
    if isinstance(error, LookupError):
        return "Restaurante não encontrado."
    if isinstance(error, RuntimeError):
        if "fleet" in str(error).casefold() or "frota" in str(error).casefold():
            return "Gere uma frota antes de buscar."
        return "Não foi possível carregar a malha viária."
    return "Ocorreu um erro inesperado."
