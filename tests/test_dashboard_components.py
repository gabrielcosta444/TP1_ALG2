from collections.abc import Iterator

from dashboard.components import build_layout


def _walk(component: object) -> Iterator[object]:
    yield component
    children = getattr(component, "children", None)
    if children is None or isinstance(children, (str, int, float)):
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
        return
    yield from _walk(children)


def _components_by_id(layout: object) -> dict[str, object]:
    return {
        identifier: component
        for component in _walk(layout)
        if (identifier := getattr(component, "id", None)) is not None
    }


def test_layout_exposes_controls_results_and_stable_ids() -> None:
    components = _components_by_id(build_layout())

    assert {
        "restaurant-select",
        "courier-count",
        "seed",
        "radius-km",
        "generate-button",
        "search-button",
        "status-message",
        "fleet-revision",
        "operation-loading",
        "map",
        "restaurant-layer",
        "courier-layer",
        "metric-candidates",
        "metric-matches",
        "metric-prefix",
        "metric-elapsed",
        "results-table",
    } <= set(components)
    assert components["courier-count"].value == 100
    assert components["seed"].value == 42
    assert components["radius-km"].value == 2
    assert components["generate-button"].children == "Gerar entregadores"
    assert components["search-button"].children == "Buscar próximos"
    assert components["operation-loading"].__class__.__name__ == "Loading"
    assert components["operation-loading"].type == "circle"
    assert components["operation-loading"].delay_show == 250


def test_layout_starts_empty_with_guidance_and_valid_geojson() -> None:
    components = _components_by_id(build_layout())

    assert components["status-message"].children == (
        "Gere uma frota e selecione um restaurante para começar."
    )
    assert components["courier-layer"].data == {
        "type": "FeatureCollection",
        "features": [],
    }
    assert components["restaurant-layer"].data == {
        "type": "FeatureCollection",
        "features": [],
    }
    assert components["results-table"].__class__.__module__.startswith("dash_ag_grid")
    assert components["results-table"].rowData == []
    numeric_columns = components["results-table"].columnDefs[1:]
    assert all(column["type"] == "numericColumn" for column in numeric_columns)
    assert all("valueFormatter" in column for column in numeric_columns)
    assert (
        components["results-table"]
        .dashGridOptions["paginationPageSizeSelector"]
        is False
    )
    assert components["metric-candidates"].children == "—"


def test_layout_shows_startup_error_and_disables_actions() -> None:
    components = _components_by_id(
        build_layout("Base processada não encontrada. Execute o script de preparação.")
    )

    assert components["status-message"].children.startswith(
        "Base processada não encontrada"
    )
    assert components["generate-button"].disabled is True
    assert components["search-button"].disabled is True
