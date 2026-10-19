from tp1.models import (
    Coordinate,
    Courier,
    CourierMatch,
    Restaurant,
    SearchMetrics,
    SearchResult,
)

from dashboard.presentation import (
    courier_feature_collection,
    error_message,
    generation_view,
    restaurant_feature_collection,
    restaurant_options,
    result_metrics,
    result_rows,
    search_view,
    zoom_for_radius,
)


def test_restaurant_options_show_name_neighborhood_and_address() -> None:
    restaurants = (
        Restaurant(
            "r1",
            "Café Central",
            "Rua A, 10",
            "Centro",
            Coordinate(-19.92, -43.94),
        ),
        Restaurant(
            "r2",
            "Bar da Praça",
            "Rua B, 20",
            "Savassi",
            Coordinate(-19.93, -43.93),
        ),
    )

    assert restaurant_options(restaurants) == [
        {"label": "Café Central — Centro — Rua A, 10", "value": "r1"},
        {"label": "Bar da Praça — Savassi — Rua B, 20", "value": "r2"},
    ]


def test_courier_feature_collection_is_one_ordered_geojson_payload() -> None:
    couriers = tuple(
        Courier(
            id=f"courier-{index:05d}",
            coordinate=Coordinate(-19.92, -43.94),
            geohash="7h2x4abc",
        )
        for index in range(10_000)
    )

    collection = courier_feature_collection(
        couriers, matched_ids={"courier-00000"}
    )

    assert collection["type"] == "FeatureCollection"
    assert len(collection["features"]) == 10_000
    assert collection["features"][0]["properties"] == {
        "id": "courier-00000",
        "category": "matched",
        "label": "courier-00000",
        "color": "#dc2626",
    }
    assert collection["features"][-1]["properties"]["category"] == "rejected"
    assert collection["features"][-1]["properties"]["color"] == "#80868b"


def test_empty_and_restaurant_feature_collections_are_valid_geojson() -> None:
    restaurant = Restaurant(
        "r1",
        "Café Central",
        "Rua A, 10",
        "Centro",
        Coordinate(-19.92, -43.94),
    )

    assert courier_feature_collection(())["features"] == []
    assert restaurant_feature_collection(None)["features"] == []
    assert restaurant_feature_collection(restaurant) == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-43.94, -19.92]},
                "properties": {
                    "id": "r1",
                    "category": "restaurant",
                    "label": "Café Central",
                    "color": "#163a5f",
                },
            }
        ],
    }


def _search_result() -> tuple[SearchResult, tuple[Courier, ...]]:
    restaurant = Restaurant(
        "r1",
        "Café Central",
        "Rua A, 10",
        "Centro",
        Coordinate(-19.92, -43.94),
    )
    matched = Courier("c1", Coordinate(-19.921, -43.94), "7h2x4abc")
    rejected = Courier("c2", Coordinate(-19.95, -43.94), "7h2x4def")
    result = SearchResult(
        restaurant=restaurant,
        matches=(CourierMatch(matched, 0.5, 1.5),),
        rejected_ids=("c2",),
        metrics=SearchMetrics(5, 9, 2, 1, 1.23456),
    )
    return result, (matched, rejected)


def test_result_rows_and_metrics_use_readable_precision() -> None:
    result, _ = _search_result()

    assert result_rows(result) == [
        {"id": "c1", "distance_km": 0.5, "eta_minutes": 1.5}
    ]
    assert result_metrics(result) == {
        "candidates": "2",
        "matches": "1",
        "prefix": "5",
        "elapsed": "1.235 ms",
    }
    assert result_rows(None) == []
    assert result_metrics(None) == {
        "candidates": "—",
        "matches": "—",
        "prefix": "—",
        "elapsed": "—",
    }


def test_generation_and_search_views_describe_complete_screen_state() -> None:
    result, couriers = _search_result()

    generated = generation_view(couriers)
    searched = search_view(result, couriers, radius_km=2.0)

    assert generated.restaurant_data["features"] == []
    assert generated.rows == []
    assert generated.metrics["matches"] == "—"
    assert {
        feature["properties"]["category"]
        for feature in generated.courier_data["features"]
    } == {"rejected"}
    assert generated.message == "2 entregadores gerados."

    assert searched.center == [-19.92, -43.94]
    assert searched.zoom == 13
    assert searched.rows[0]["id"] == "c1"
    assert searched.metrics["matches"] == "1"
    assert [
        feature["properties"]["category"]
        for feature in searched.courier_data["features"]
    ] == ["matched", "rejected"]
    assert searched.message == "1 entregador encontrado."


def test_zoom_decreases_as_radius_grows() -> None:
    assert zoom_for_radius(0.5) == 15
    assert zoom_for_radius(2.0) == 13
    assert zoom_for_radius(20.0) == 10


def test_error_message_translates_known_backend_failures() -> None:
    assert error_message(ValueError("invalid count")) == (
        "Parâmetro inválido. Revise os valores informados."
    )
    assert error_message(LookupError("missing")) == "Restaurante não encontrado."
    assert error_message(RuntimeError("fleet has not been generated")) == (
        "Gere uma frota antes de buscar."
    )
    assert error_message(RuntimeError("unable to load street network")) == (
        "Não foi possível carregar a malha viária."
    )
    assert error_message(OSError("unexpected")) == "Ocorreu um erro inesperado."
