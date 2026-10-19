
import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import logging
from math import isfinite
from pathlib import Path
from threading import RLock

from dash import Dash, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from dashboard.components import build_layout
from dashboard.presentation import (
    DashboardView,
    error_message,
    generation_view,
    restaurant_options,
    search_view,
)
from tp1.models import Courier, Restaurant
from tp1.restaurants import RestaurantRepository
from tp1.service import FleetService
from tp1.simulation import CourierGenerator, OsmnxStreetSnapper, StreetSnapper

LOGGER = logging.getLogger(__name__)

APP_TITLE = (
    "Trabalho Prático 1 — Indexação Geoespacial e "
    "Geometria Computacional Híbrida"
)

INDEX_TEMPLATE_WITHOUT_FAVICON = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""


@dataclass(frozen=True, slots=True)
class DashboardActionResult:
    view: DashboardView | None
    revision: int
    message: str
    error: bool


class LazyCourierGenerator:

    def __init__(
        self,
        restaurants: Sequence[Restaurant],
        cache_path: Path,
        snapper_factory: Callable[[Path], StreetSnapper] = (
            OsmnxStreetSnapper.from_place
        ),
    ) -> None:
        self._restaurants = tuple(restaurants)
        self._cache_path = cache_path
        self._snapper_factory = snapper_factory
        self._generator: CourierGenerator | None = None
        self._lock = RLock()

    def generate(
        self,
        count: int,
        seed: int | None = None,
        standard_deviation_m: float = 800.0,
    ) -> tuple[Courier, ...]:
        with self._lock:
            if self._generator is None:
                snapper = self._snapper_factory(self._cache_path)
                self._generator = CourierGenerator(self._restaurants, snapper)
            return self._generator.generate(count, seed, standard_deviation_m)


class DashboardController:

    def __init__(self, service: FleetService) -> None:
        self._service = service
        self._lock = RLock()

    def options(self, text: str | None) -> list[dict[str, str]]:
        with self._lock:
            restaurants = self._service.search_restaurants(
                (text or "").strip(), limit=20
            )
            return restaurant_options(restaurants)

    def generate(self, count: object, seed: object) -> DashboardView:
        parsed_count = _parse_integer(count, "count")
        if not 1 <= parsed_count <= 10_000:
            raise ValueError("count must be between 1 and 10000")
        parsed_seed = _parse_integer(seed, "seed", allow_none=True)
        with self._lock:
            couriers = self._service.generate_couriers(
                parsed_count,
                parsed_seed,
                standard_deviation_m=800.0,
            )
            return generation_view(couriers)

    def search(
        self, restaurant_id: str | None, radius_km: object
    ) -> DashboardView:
        if not isinstance(restaurant_id, str) or not restaurant_id.strip():
            raise ValueError("restaurant must be selected")
        radius = _parse_radius(radius_km)
        with self._lock:
            result = self._service.search_nearby(restaurant_id, radius)
            return search_view(result, self._service.couriers, radius)


def handle_action(
    controller: DashboardController,
    action: str,
    count: object,
    seed: object,
    restaurant_id: str | None,
    radius_km: object,
    revision: int,
) -> DashboardActionResult:
    try:
        if action == "generate-button":
            view = controller.generate(count, seed)
            return DashboardActionResult(view, revision + 1, view.message, False)
        if action == "search-button":
            view = controller.search(restaurant_id, radius_km)
            return DashboardActionResult(view, revision, view.message, False)
        raise ValueError("unknown dashboard action")
    except Exception as error:
        if not isinstance(error, (ValueError, LookupError, RuntimeError)):
            LOGGER.exception("unexpected dashboard action failure")
        return DashboardActionResult(
            view=None,
            revision=revision,
            message=error_message(error),
            error=True,
        )


def create_controller(
    restaurants_path: Path, street_cache_path: Path
) -> DashboardController:
    if not restaurants_path.is_file():
        raise FileNotFoundError(
            "Base processada não encontrada. Execute o script de preparação "
            f"para criar {restaurants_path}."
        )
    repository = RestaurantRepository.from_csv(restaurants_path)
    generator = LazyCourierGenerator(repository.all(), street_cache_path)
    return DashboardController(FleetService(repository, generator))


def create_app(
    controller: DashboardController | None,
    startup_error: str | None = None,
) -> Dash:
    app = Dash(
        __name__,
        title=APP_TITLE,
        assets_folder=str(Path(__file__).parent / "assets"),
    )
    app.index_string = INDEX_TEMPLATE_WITHOUT_FAVICON
    app.layout = build_layout(startup_error)

    @app.callback(
        Output("restaurant-select", "options"),
        Input("restaurant-select", "search_value"),
        State("restaurant-select", "value"),
        State("restaurant-select", "options"),
    )
    def update_restaurant_options(
        search_value: str | None,
        selected_value: str | None,
        current_options: list[dict[str, str]] | None,
    ):
        if controller is None:
            return []
        options = controller.options(search_value)
        if selected_value is None or any(
            option.get("value") == selected_value for option in options
        ):
            return options

        selected_option = next(
            (
                option
                for option in (current_options or [])
                if option.get("value") == selected_value
            ),
            None,
        )
        if selected_option is None:
            return options
        return [selected_option, *options]

    @app.callback(
        Output("courier-layer", "data"),
        Output("restaurant-layer", "data"),
        Output("results-table", "rowData"),
        Output("metric-candidates", "children"),
        Output("metric-matches", "children"),
        Output("metric-prefix", "children"),
        Output("metric-elapsed", "children"),
        Output("map", "center"),
        Output("map", "zoom"),
        Output("status-message", "children"),
        Output("status-message", "className"),
        Output("fleet-revision", "data"),
        Input("generate-button", "n_clicks"),
        Input("search-button", "n_clicks"),
        State("courier-count", "value"),
        State("seed", "value"),
        State("restaurant-select", "value"),
        State("radius-km", "value"),
        State("fleet-revision", "data"),
        prevent_initial_call=True,
        running=[
            (Output("generate-button", "disabled"), True, False),
            (Output("search-button", "disabled"), True, False),
        ],
    )
    def update_dashboard(
        generate_clicks: int,
        search_clicks: int,
        count: object,
        seed: object,
        restaurant_id: str | None,
        radius_km: object,
        revision: int | None,
    ):
        del generate_clicks, search_clicks
        if controller is None or ctx.triggered_id is None:
            raise PreventUpdate
        current_revision = revision if isinstance(revision, int) else 0
        result = handle_action(
            controller,
            action=ctx.triggered_id,
            count=count,
            seed=seed,
            restaurant_id=restaurant_id,
            radius_km=radius_km,
            revision=current_revision,
        )
        if result.view is None:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                result.message,
                "status-message status-error",
                result.revision,
            )
        view = result.view
        return (
            view.courier_data,
            view.restaurant_data,
            view.rows,
            view.metrics["candidates"],
            view.metrics["matches"],
            view.metrics["prefix"],
            view.metrics["elapsed"],
            view.center,
            view.zoom,
            view.message,
            "status-message",
            result.revision,
        )

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa o dashboard local do Trabalho Prático 1."
    )
    parser.add_argument(
        "--restaurants",
        type=Path,
        default=Path("data/processed/restaurants.csv"),
        help="CSV processado de restaurantes",
    )
    parser.add_argument(
        "--street-cache",
        type=Path,
        default=Path("data/cache/bh_drive.graphml"),
        help="cache GraphML da malha viária",
    )
    parser.add_argument("--host", default="127.0.0.1", help="endereço do servidor")
    parser.add_argument("--port", type=int, default=8050, help="porta do servidor")
    parser.add_argument("--debug", action="store_true", help="ativa o modo debug")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        controller = create_controller(
            arguments.restaurants, arguments.street_cache
        )
        startup_error = None
    except FileNotFoundError as error:
        controller = None
        startup_error = str(error)
    except Exception:
        LOGGER.exception("failed to initialize dashboard")
        controller = None
        startup_error = "Não foi possível carregar a base processada."

    app = create_app(controller, startup_error)
    app.run(host=arguments.host, port=arguments.port, debug=arguments.debug)
    return 0


def _parse_integer(
    value: object, field: str, allow_none: bool = False
) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be an integer")
    if not isfinite(float(value)) or not float(value).is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(value)


def _parse_radius(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("radius must be numeric")
    radius = float(value)
    if not isfinite(radius) or not 0.0 < radius <= 20.0:
        raise ValueError("radius must be positive and no greater than 20")
    return radius


if __name__ == "__main__":
    raise SystemExit(main())
