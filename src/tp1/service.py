
from math import isfinite
from time import perf_counter

from tp1.geohash import prefixes_for_radius
from tp1.geometry import estimate_eta_minutes, haversine_km
from tp1.models import (
    Courier,
    CourierMatch,
    Restaurant,
    SearchMetrics,
    SearchResult,
)
from tp1.restaurants import RestaurantRepository
from tp1.simulation import CourierGenerator
from tp1.trie import RadixTrie


class FleetService:
    def __init__(
        self, repository: RestaurantRepository, generator: CourierGenerator
    ) -> None:
        self._repository = repository
        self._generator = generator
        self._couriers: tuple[Courier, ...] = ()
        self._couriers_by_id: dict[str, Courier] = {}
        self._index = RadixTrie()

    @property
    def couriers(self) -> tuple[Courier, ...]:
        return self._couriers

    def generate_couriers(
        self,
        count: int,
        seed: int | None = None,
        standard_deviation_m: float = 800.0,
    ) -> tuple[Courier, ...]:
        generated = tuple(
            self._generator.generate(count, seed, standard_deviation_m)
        )
        if len(generated) != count:
            raise RuntimeError("generator returned an unexpected courier count")

        new_index = RadixTrie()
        new_by_id: dict[str, Courier] = {}
        for courier in generated:
            if courier.id in new_by_id:
                raise ValueError(f"duplicate courier id: {courier.id}")
            new_index.insert(courier.geohash, courier.id)
            new_by_id[courier.id] = courier

        self._couriers = generated
        self._couriers_by_id = new_by_id
        self._index = new_index
        return generated

    def search_restaurants(
        self, text: str, limit: int = 20
    ) -> tuple[Restaurant, ...]:
        return self._repository.search(text, limit)

    def search_nearby(
        self,
        restaurant_id: str,
        radius_km: float,
        speed_kmh: float = 20.0,
    ) -> SearchResult:
        if not isfinite(radius_km) or not 0.0 < radius_km <= 20.0:
            raise ValueError("radius_km must be positive and no greater than 20")
        if not isfinite(speed_kmh) or speed_kmh <= 0.0:
            raise ValueError("speed_kmh must be positive and finite")

        restaurant = self._repository.get(restaurant_id)
        if not self._couriers:
            raise RuntimeError("fleet has not been generated")

        started_at = perf_counter()
        prefixes = prefixes_for_radius(restaurant.coordinate, radius_km)
        candidate_ids: dict[str, None] = {}
        for prefix in prefixes:
            for courier_id in self._index.search_prefix(prefix):
                candidate_ids[courier_id] = None

        matches: list[CourierMatch] = []
        for courier_id in candidate_ids:
            courier = self._couriers_by_id[courier_id]
            distance_km = haversine_km(restaurant.coordinate, courier.coordinate)
            if distance_km <= radius_km + 1e-9:
                matches.append(
                    CourierMatch(
                        courier=courier,
                        distance_km=distance_km,
                        eta_minutes=estimate_eta_minutes(distance_km, speed_kmh),
                    )
                )

        matches.sort(key=lambda match: (match.distance_km, match.courier.id))
        matched_ids = {match.courier.id for match in matches}
        rejected_ids = tuple(
            courier.id for courier in self._couriers if courier.id not in matched_ids
        )
        elapsed_ms = (perf_counter() - started_at) * 1000.0
        metrics = SearchMetrics(
            prefix_length=len(prefixes[0]),
            prefixes_visited=len(prefixes),
            candidates=len(candidate_ids),
            matches=len(matches),
            elapsed_ms=elapsed_ms,
        )
        return SearchResult(
            restaurant=restaurant,
            matches=tuple(matches),
            rejected_ids=rejected_ids,
            metrics=metrics,
        )
