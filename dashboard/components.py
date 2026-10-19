
from dash import dcc, html
import dash_ag_grid as dag
import dash_leaflet as dl
from dash_extensions.javascript import variable

from dashboard.presentation import result_metrics

_EMPTY_GEOJSON = {"type": "FeatureCollection", "features": []}
_BH_CENTER = [-19.9167, -43.9345]

geojson_point_to_layer = variable(
    "dashExtensions", "default", "function0"
)


def _metric_card(label: str, component_id: str, value: str) -> html.Div:
    return html.Div(
        className="metric-card",
        children=[
            html.Span(label, className="metric-label"),
            html.Strong(value, id=component_id, className="metric-value"),
        ],
    )


def build_layout(startup_error: str | None = None) -> html.Div:
    metrics = result_metrics(None)
    status = startup_error or (
        "Gere uma frota e selecione um restaurante para começar."
    )
    actions_disabled = startup_error is not None

    return html.Div(
        className="app-shell",
        children=[
            dcc.Store(id="fleet-revision", data=0),
            html.Header(
                className="page-header",
                children=[
                    html.H1("Trabalho Prático 1"),
                    html.P(
                        "Indexação Geoespacial e Geometria Computacional "
                        "Híbrida"
                    ),
                ],
            ),
            html.Main(
                className="page-grid",
                children=[
                    html.Aside(
                        className="control-panel",
                        children=[
                            html.H2("Controles"),
                            html.Label("Restaurante", htmlFor="restaurant-select"),
                            dcc.Dropdown(
                                id="restaurant-select",
                                options=[],
                                placeholder="Digite nome, endereço ou bairro",
                                searchable=True,
                                clearable=True,
                                disabled=actions_disabled,
                            ),
                            html.Label(
                                "Quantidade de entregadores",
                                htmlFor="courier-count",
                            ),
                            dcc.Input(
                                id="courier-count",
                                type="number",
                                value=100,
                                min=1,
                                max=10_000,
                                step=1,
                                disabled=actions_disabled,
                            ),
                            html.Label("Semente", htmlFor="seed"),
                            dcc.Input(
                                id="seed",
                                type="number",
                                value=42,
                                step=1,
                                disabled=actions_disabled,
                            ),
                            html.Label("Raio (km)", htmlFor="radius-km"),
                            dcc.Input(
                                id="radius-km",
                                type="number",
                                value=2,
                                min=0.1,
                                max=20,
                                step=0.1,
                                disabled=actions_disabled,
                            ),
                            html.Button(
                                "Gerar entregadores",
                                id="generate-button",
                                n_clicks=0,
                                className="primary-button",
                                disabled=actions_disabled,
                            ),
                            html.Button(
                                "Buscar próximos",
                                id="search-button",
                                n_clicks=0,
                                className="primary-button",
                                disabled=actions_disabled,
                            ),
                            html.Div(
                                status,
                                id="status-message",
                                className=(
                                    "status-message status-error"
                                    if startup_error
                                    else "status-message"
                                ),
                                role="status",
                                **{"aria-live": "polite"},
                            ),
                        ],
                    ),
                    dcc.Loading(
                        id="operation-loading",
                        type="circle",
                        delay_show=250,
                        children=html.Section(
                            className="results-panel",
                            children=[
                            dl.Map(
                                id="map",
                                center=_BH_CENTER,
                                zoom=12,
                                className="map-container",
                                children=[
                                    dl.TileLayer(),
                                    dl.GeoJSON(
                                        id="courier-layer",
                                        data=_EMPTY_GEOJSON,
                                        options={
                                            "pointToLayer": geojson_point_to_layer
                                        },
                                    ),
                                    dl.GeoJSON(
                                        id="restaurant-layer",
                                        data=_EMPTY_GEOJSON,
                                        options={
                                            "pointToLayer": geojson_point_to_layer
                                        },
                                    ),
                                ],
                            ),
                            html.Div(
                                className="metrics-grid",
                                children=[
                                    _metric_card(
                                        "Candidatos",
                                        "metric-candidates",
                                        metrics["candidates"],
                                    ),
                                    _metric_card(
                                        "Encontrados",
                                        "metric-matches",
                                        metrics["matches"],
                                    ),
                                    _metric_card(
                                        "Prefixo",
                                        "metric-prefix",
                                        metrics["prefix"],
                                    ),
                                    _metric_card(
                                        "Tempo da busca",
                                        "metric-elapsed",
                                        metrics["elapsed"],
                                    ),
                                ],
                            ),
                            html.Div(
                                className="table-card",
                                children=[
                                    html.H2("Entregadores encontrados"),
                                    dag.AgGrid(
                                        id="results-table",
                                        columnDefs=[
                                            {
                                                "headerName": "ID",
                                                "field": "id",
                                            },
                                            {
                                                "headerName": "Distância (km)",
                                                "field": "distance_km",
                                                "type": "numericColumn",
                                                "valueFormatter": {
                                                    "function": (
                                                        "params.value == null ? '' : "
                                                        "Number(params.value).toFixed(2)"
                                                    )
                                                },
                                            },
                                            {
                                                "headerName": "ETA (min)",
                                                "field": "eta_minutes",
                                                "type": "numericColumn",
                                                "valueFormatter": {
                                                    "function": (
                                                        "params.value == null ? '' : "
                                                        "Number(params.value).toFixed(2)"
                                                    )
                                                },
                                            },
                                        ],
                                        rowData=[],
                                        defaultColDef={
                                            "sortable": True,
                                            "resizable": True,
                                            "flex": 1,
                                            "minWidth": 120,
                                        },
                                        dashGridOptions={
                                            "pagination": True,
                                            "paginationPageSize": 15,
                                            "paginationPageSizeSelector": False,
                                        },
                                        style={"height": "480px", "width": "100%"},
                                    ),
                                ],
                            ),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )
