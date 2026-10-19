from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from time import sleep

import pytest

from dashboard.app import (
    DashboardController,
    LazyCourierGenerator,
    build_parser,
    create_app,
    create_controller,
    handle_action,
)
from tp1.models import (
    Coordinate,
    Courier,
    CourierMatch,
    Restaurant,
    SearchMetrics,
    SearchResult,
)


class IdentitySnapper:
    def snap_all(
        self, coordinates: tuple[Coordinate, ...]
    ) -> tuple[Coordinate, ...]:
        return tuple(coordinates)


def _restaurant() -> Restaurant:
    return Restaurant(
        "r1",
        "Café Central",
        "Rua A, 10",
        "Centro",
        Coordinate(-19.92, -43.94),
    )


def _courier(identifier: str = "c1") -> Courier:
    return Courier(identifier, Coordinate(-19.921, -43.94), "7h2x4abc")


def _result(courier: Courier | None = None) -> SearchResult:
    selected = courier or _courier()
    return SearchResult(
        restaurant=_restaurant(),
        matches=(CourierMatch(selected, 0.5, 1.5),),
        rejected_ids=(),
        metrics=SearchMetrics(5, 9, 1, 1, 0.25),
    )


class FakeService:
    def __init__(self) -> None:
        self.couriers: tuple[Courier, ...] = ()
        self.generation_calls: list[tuple[int, int | None, float]] = []
        self.search_calls: list[tuple[str, float]] = []

    def search_restaurants(self, text: str, limit: int = 20):
        assert limit == 20
        return (_restaurant(),) if text.casefold() in "café central".casefold() else ()

    def generate_couriers(
        self,
        count: int,
        seed: int | None = None,
        standard_deviation_m: float = 800.0,
    ) -> tuple[Courier, ...]:
        self.generation_calls.append((count, seed, standard_deviation_m))
        self.couriers = tuple(_courier(f"c{index}") for index in range(count))
        return self.couriers

    def search_nearby(
        self, restaurant_id: str, radius_km: float, speed_kmh: float = 20.0
    ) -> SearchResult:
        self.search_calls.append((restaurant_id, radius_km))
        return _result(self.couriers[0])


def test_lazy_generator_creates_and_reuses_snapper_on_first_generation() -> None:
    calls: list[Path] = []

    def snapper_factory(path: Path) -> IdentitySnapper:
        calls.append(path)
        return IdentitySnapper()

    generator = LazyCourierGenerator(
        (_restaurant(),), Path("streets.graphml"), snapper_factory
    )

    assert calls == []
    assert len(generator.generate(1, seed=7, standard_deviation_m=0.0)) == 1
    assert len(generator.generate(1, seed=8, standard_deviation_m=0.0)) == 1
    assert calls == [Path("streets.graphml")]


def test_controller_formats_options_and_generation_view() -> None:
    service = FakeService()
    controller = DashboardController(service)

    assert controller.options("central") == [
        {"label": "Café Central — Centro — Rua A, 10", "value": "r1"}
    ]
    view = controller.generate(2, 42)

    assert service.generation_calls == [(2, 42, 800.0)]
    assert view.message == "2 entregadores gerados."
    assert len(view.courier_data["features"]) == 2


@pytest.mark.parametrize(
    "count, seed",
    [(None, 42), (0, 42), (10_001, 42), (2.5, 42), (True, 42), (2, 1.5)],
)
def test_controller_rejects_invalid_generation_fields_without_calling_service(
    count: object, seed: object
) -> None:
    service = FakeService()
    controller = DashboardController(service)

    with pytest.raises(ValueError):
        controller.generate(count, seed)

    assert service.generation_calls == []


def test_controller_builds_search_view_and_validates_selection() -> None:
    service = FakeService()
    controller = DashboardController(service)
    controller.generate(1, 42)

    with pytest.raises(ValueError):
        controller.search(None, 2.0)
    with pytest.raises(ValueError):
        controller.search("r1", None)

    view = controller.search("r1", 2.0)

    assert service.search_calls == [("r1", 2.0)]
    assert view.message == "1 entregador encontrado."
    assert view.center == [-19.92, -43.94]


def test_controller_serializes_concurrent_service_calls() -> None:
    class ReentryDetectingService(FakeService):
        def __init__(self) -> None:
            super().__init__()
            self._guard = Lock()
            self._active = 0

        def generate_couriers(self, count, seed=None, standard_deviation_m=800.0):
            with self._guard:
                self._active += 1
                if self._active > 1:
                    raise RuntimeError("concurrent service access")
            sleep(0.02)
            try:
                return super().generate_couriers(count, seed, standard_deviation_m)
            finally:
                with self._guard:
                    self._active -= 1

    controller = DashboardController(ReentryDetectingService())

    with ThreadPoolExecutor(max_workers=4) as executor:
        views = list(executor.map(lambda seed: controller.generate(1, seed), range(4)))

    assert [view.message for view in views] == ["1 entregador gerado."] * 4


def test_handle_action_preserves_visual_state_when_validation_fails() -> None:
    controller = DashboardController(FakeService())

    generated = handle_action(
        controller,
        action="generate-button",
        count=1,
        seed=42,
        restaurant_id=None,
        radius_km=2.0,
        revision=3,
    )
    failed = handle_action(
        controller,
        action="search-button",
        count=1,
        seed=42,
        restaurant_id=None,
        radius_km=2.0,
        revision=generated.revision,
    )

    assert generated.view is not None
    assert generated.revision == 4
    assert generated.error is False
    assert failed.view is None
    assert failed.revision == 4
    assert failed.message == "Parâmetro inválido. Revise os valores informados."
    assert failed.error is True


def test_handle_action_translates_network_failure_without_losing_revision() -> None:
    class FailingService(FakeService):
        def generate_couriers(self, *args, **kwargs):
            raise RuntimeError("unable to load or download street network")

    result = handle_action(
        DashboardController(FailingService()),
        action="generate-button",
        count=10,
        seed=42,
        restaurant_id=None,
        radius_km=2.0,
        revision=7,
    )

    assert result.view is None
    assert result.revision == 7
    assert result.message == "Não foi possível carregar a malha viária."
    assert result.error is True


def test_create_app_registers_search_and_action_callbacks() -> None:
    app = create_app(DashboardController(FakeService()))

    assert app.title == (
        "Trabalho Prático 1 — Indexação Geoespacial e "
        "Geometria Computacional Híbrida"
    )
    assert len(app.callback_map) == 2
    assert "restaurant-select.options" in app.callback_map
    assert any("courier-layer.data" in key for key in app.callback_map)


def test_restaurant_options_keep_the_selected_search_result() -> None:
    selected = {"label": "Restaurante pesquisado", "value": "r-selected"}
    initial = {"label": "Restaurante inicial", "value": "r-initial"}

    class DynamicOptionsController:
        def options(self, text: str | None):
            return [selected] if text else [initial]

    app = create_app(DynamicOptionsController())
    response = app.server.test_client().post(
        "/_dash-update-component",
        json={
            "output": "restaurant-select.options",
            "outputs": {
                "id": "restaurant-select",
                "property": "options",
            },
            "inputs": [
                {
                    "id": "restaurant-select",
                    "property": "search_value",
                    "value": None,
                }
            ],
            "state": [
                {
                    "id": "restaurant-select",
                    "property": "value",
                    "value": "r-selected",
                },
                {
                    "id": "restaurant-select",
                    "property": "options",
                    "value": [selected],
                },
            ],
            "changedPropIds": ["restaurant-select.search_value"],
        },
    )

    assert response.status_code == 200
    options = response.get_json()["response"]["restaurant-select"]["options"]
    assert options == [selected, initial]


def test_create_app_does_not_publish_a_favicon() -> None:
    app = create_app(DashboardController(FakeService()))

    response = app.server.test_client().get("/")

    assert response.status_code == 200
    assert b'rel="icon"' not in response.data
    assert b"_favicon.ico" not in response.data


def test_action_callback_disables_buttons_while_processing() -> None:
    app = create_app(DashboardController(FakeService()))

    dependencies = app.server.test_client().get(
        "/_dash-dependencies"
    ).get_json()
    action_callback = next(
        item for item in dependencies if "courier-layer.data" in item["output"]
    )

    assert action_callback["running"] == {
        "running": {
            "generate-button.disabled": True,
            "search-button.disabled": True,
        },
        "runningOff": {
            "generate-button.disabled": False,
            "search-button.disabled": False,
        },
    }


def test_create_app_serves_marker_javascript_asset() -> None:
    app = create_app(DashboardController(FakeService()))
    client = app.server.test_client()

    index_response = client.get("/")
    response = client.get("/assets/dashExtensions_default.js")

    assert response.status_code == 200
    assert response.content_type.startswith("text/javascript")
    assert b"window.dashExtensions" in response.data
    assert b"function0" in response.data
    assert b"/assets/dashExtensions_default.js" in index_response.data


def test_missing_dataset_can_be_rendered_as_startup_error(tmp_path: Path) -> None:
    missing = tmp_path / "restaurants.csv"

    with pytest.raises(FileNotFoundError, match="Base processada"):
        create_controller(missing, tmp_path / "streets.graphml")

    app = create_app(None, "Base processada não encontrada.")
    assert app.layout is not None


def test_dashboard_parser_accepts_paths_server_and_debug_options() -> None:
    arguments = build_parser().parse_args(
        [
            "--restaurants",
            "restaurants.csv",
            "--street-cache",
            "streets.graphml",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--debug",
        ]
    )

    assert arguments.restaurants == Path("restaurants.csv")
    assert arguments.street_cache == Path("streets.graphml")
    assert arguments.host == "0.0.0.0"
    assert arguments.port == 9000
    assert arguments.debug is True
