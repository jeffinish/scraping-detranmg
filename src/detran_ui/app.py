"""App NiceGUI: filtros, cards, flag de interesse, proxy da foto da listagem."""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from math import ceil

import httpx
from dotenv import load_dotenv
from fastapi.responses import Response
from nicegui import app, ui
from sqlalchemy.engine import Engine

from detran_scraper.client import DEFAULT_HEADERS
from detran_scraper.storage import create_db_engine
from detran_ui.queries import (
    LoteFiltros,
    apply_schema,
    count_interesse,
    get_leilao_id,
    list_lotes,
    list_opcoes,
    set_interesse,
    url_imagem,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 24
CACHE_TTL_S = 300.0
CACHE_MAX = 256

_engine: Engine | None = None
_http = httpx.Client(headers=DEFAULT_HEADERS, timeout=20.0, follow_redirects=True)
_img_cache: OrderedDict[int, tuple[float, bytes, str]] = OrderedDict()

_PLACEHOLDER = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240">'
    b'<rect fill="#ECEFF1" width="100%" height="100%"/>'
    b'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
    b'fill="#90A4AE" font-family="Roboto,sans-serif" font-size="16">Sem foto</text>'
    b"</svg>"
)


def _db() -> Engine:
    if _engine is None:
        raise RuntimeError("Engine não inicializada")
    return _engine


def _placeholder() -> Response:
    return Response(content=_PLACEHOLDER, media_type="image/svg+xml")


@app.get("/imagens/{lote_id}")
def proxy_imagem(lote_id: int) -> Response:
    """Busca o thumbnail no portal (headers de browser) e devolve ao card."""
    now = time.monotonic()
    cached = _img_cache.get(lote_id)
    if cached is not None and cached[0] > now:
        _img_cache.move_to_end(lote_id)
        return Response(content=cached[1], media_type=cached[2])

    leilao_id = get_leilao_id(_db(), lote_id)
    if leilao_id is None:
        return _placeholder()

    try:
        response = _http.get(url_imagem(leilao_id, lote_id))
        if response.status_code != 200 or not response.content:
            return _placeholder()
        content_type = response.headers.get("content-type", "image/jpeg")
        if not content_type.startswith("image/"):
            return _placeholder()
        _img_cache[lote_id] = (now + CACHE_TTL_S, response.content, content_type)
        _img_cache.move_to_end(lote_id)
        while len(_img_cache) > CACHE_MAX:
            _img_cache.popitem(last=False)
        return Response(content=response.content, media_type=content_type)
    except httpx.HTTPError:
        logger.debug("Falha ao buscar imagem do lote %s", lote_id, exc_info=True)
        return _placeholder()


def _filtros_iniciais(opcoes: dict[str, list[str]]) -> LoteFiltros:
    ativos = [s for s in ("Publicado", "Em Andamento") if s in opcoes["status_edital"]]
    return LoteFiltros(status_edital=ativos)


@ui.page("/")
def index() -> None:
    ui.colors(primary="#1565C0", secondary="#455A64", accent="#00897B")
    ui.query("body").classes("bg-grey-2")

    try:
        opcoes = list_opcoes(_db())
    except Exception as exc:
        with ui.card().classes("m-8 p-6 max-w-lg mx-auto"):
            ui.label("Banco indisponível").classes("text-h6")
            ui.label(str(exc)).classes("text-grey-8")
            ui.label(
                "Suba o Postgres (`docker compose up -d`) e rode "
                "`python -m detran_scraper.run --lotes`."
            ).classes("mt-2")
        return

    filtros = _filtros_iniciais(opcoes)
    state = {"page": 1}
    ready = False

    def sync_from_widgets() -> None:
        filtros.marcas = list(marcas.value or [])
        filtros.modelo_contem = (modelo.value or "").strip()
        filtros.municipios = list(municipios.value or [])
        filtros.condicoes = list(condicoes.value or [])
        filtros.status_edital = list(status.value or [])
        filtros.valor_min = valor_min.value
        filtros.valor_max = valor_max.value
        filtros.ano_min = int(ano_min.value) if ano_min.value is not None else None
        filtros.ano_max = int(ano_max.value) if ano_max.value is not None else None
        filtros.somente_interesse = bool(somente.value)

    def aplicar(_e=None) -> None:
        if not ready:
            return
        state["page"] = 1
        sync_from_widgets()
        painel.refresh()

    def limpar(_e=None) -> None:
        inicial = _filtros_iniciais(opcoes)
        marcas.value = []
        modelo.value = ""
        municipios.value = []
        condicoes.value = []
        status.value = list(inicial.status_edital)
        valor_min.value = None
        valor_max.value = None
        ano_min.value = None
        ano_max.value = None
        somente.value = False
        aplicar()

    def toggle(lote_id: int, flagged: bool) -> None:
        set_interesse(_db(), lote_id, flagged)
        painel.refresh()

    def abrir_detalhe(lote: dict) -> None:
        with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg p-0 overflow-hidden"):
            ui.image(f"/imagens/{lote['lote_id']}").classes("w-full h-56 object-cover")
            with ui.card_section():
                ui.label(lote["marca_modelo"]).classes("text-h6")
                with ui.row().classes("flex-wrap gap-2 mt-1"):
                    ui.chip(lote["condicao"] or "—", color="primary", text_color="white")
                    ui.chip(lote["status_edital"] or "—")
                ui.separator().classes("my-3")
                linhas = [
                    ("Valor", lote["valor_fmt"]),
                    ("Lote", lote["numero_lote"]),
                    ("Edital", lote["numero_edital"]),
                    ("Município", lote["municipio"]),
                    ("Pátio", lote["patio"]),
                    ("Ano", lote["ano_veiculo"] or "—"),
                    ("Encerramento", lote["data_encerramento"] or "—"),
                ]
                for rotulo, valor in linhas:
                    with ui.row().classes("w-full justify-between"):
                        ui.label(rotulo).classes("text-grey-7")
                        ui.label(str(valor)).classes("font-medium")
                with ui.row().classes("w-full justify-between mt-4"):
                    ui.link("Abrir no portal", lote["url_detalhes"], new_tab=True)
                    ui.button("Fechar", on_click=dialog.close).props("flat")
        dialog.open()

    with ui.header().classes("items-center px-4"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props(
            "flat round color=white"
        )
        ui.label("Lotes DETRAN/MG").classes("text-h6")
        ui.space()
        somente = (
            ui.switch("Somente interesse", value=False, on_change=aplicar)
            .props("color=amber-8")
            .classes("text-white")
        )

    drawer = ui.left_drawer(value=None, bordered=True).classes("bg-white p-4")
    with drawer:
        ui.label("Filtros").classes("text-subtitle1 text-grey-8 mb-2")
        marcas = ui.select(
            opcoes["marcas"],
            label="Marca",
            multiple=True,
            with_input=True,
            on_change=aplicar,
        ).props("outlined dense use-chips").classes("w-full")
        modelo = (
            ui.input("Modelo contém", placeholder="ex.: ONIX")
            .props("outlined dense")
            .classes("w-full")
            .on("keydown.enter", aplicar)
        )
        municipios = ui.select(
            opcoes["municipios"],
            label="Município",
            multiple=True,
            with_input=True,
            on_change=aplicar,
        ).props("outlined dense use-chips").classes("w-full")
        condicoes = ui.select(
            opcoes["condicoes"],
            label="Condição",
            multiple=True,
            on_change=aplicar,
        ).props("outlined dense use-chips").classes("w-full")
        status = ui.select(
            opcoes["status_edital"],
            label="Status do edital",
            multiple=True,
            value=list(filtros.status_edital),
            on_change=aplicar,
        ).props("outlined dense use-chips").classes("w-full")
        with ui.row().classes("w-full gap-2"):
            valor_min = (
                ui.number("Valor mín.", format="%.0f", value=None)
                .props("outlined dense")
                .classes("flex-1")
                .on("keydown.enter", aplicar)
            )
            valor_max = (
                ui.number("Valor máx.", format="%.0f", value=None)
                .props("outlined dense")
                .classes("flex-1")
                .on("keydown.enter", aplicar)
            )
        with ui.row().classes("w-full gap-2"):
            ano_min = (
                ui.number("Ano mín.", format="%.0f", value=None)
                .props("outlined dense")
                .classes("flex-1")
                .on("keydown.enter", aplicar)
            )
            ano_max = (
                ui.number("Ano máx.", format="%.0f", value=None)
                .props("outlined dense")
                .classes("flex-1")
                .on("keydown.enter", aplicar)
            )
        with ui.row().classes("w-full gap-2 mt-2"):
            ui.button("Aplicar", on_click=aplicar, icon="filter_list").props(
                "unelevated"
            ).classes("flex-1")
            ui.button("Limpar", on_click=limpar, icon="filter_alt_off").props(
                "flat"
            ).classes("flex-1")

    @ui.refreshable
    def painel() -> None:
        sync_from_widgets()
        lotes, total = list_lotes(
            _db(), filtros, page=state["page"], page_size=PAGE_SIZE
        )
        n_flag = count_interesse(_db())
        max_page = max(1, ceil(total / PAGE_SIZE) if total else 1)
        if state["page"] > max_page:
            state["page"] = max_page
            lotes, total = list_lotes(
                _db(), filtros, page=state["page"], page_size=PAGE_SIZE
            )

        with ui.row().classes("w-full items-center px-2 mb-2"):
            ui.label(f"{total:,} lotes".replace(",", ".")).classes("text-h6")
            ui.chip(f"{n_flag} de interesse", icon="star").props("outline color=amber-9")
        if total == 0:
            with ui.card().classes("w-full p-8 items-center"):
                ui.icon("search_off", size="lg").classes("text-grey-5")
                ui.label("Nenhum lote com esses filtros.").classes("text-grey-7")
            return

        with ui.element("div").classes(
            "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        ):
            for lote in lotes:
                _card(lote, toggle, abrir_detalhe)

        if max_page > 1:
            with ui.row().classes("w-full justify-center mt-4"):
                ui.pagination(
                    1,
                    max_page,
                    value=state["page"],
                    direction_links=True,
                    on_change=lambda e: (
                        state.update(page=int(e.value)),
                        painel.refresh(),
                    ),
                )

    with ui.column().classes("w-full max-w-screen-xl mx-auto p-4"):
        ready = True
        painel()


def _card(lote: dict, toggle, abrir_detalhe) -> None:
    starred = bool(lote["interesse"])
    with ui.card().classes("w-full no-shadow rounded-xl overflow-hidden"):
        ui.image(f"/imagens/{lote['lote_id']}").classes(
            "w-full h-44 object-cover cursor-pointer"
        ).on("click", lambda l=lote: abrir_detalhe(l))
        with ui.card_section().classes("p-3"):
            with ui.row().classes("w-full items-center justify-between no-wrap"):
                ui.label(lote["marca_modelo"]).classes(
                    "text-subtitle1 font-medium ellipsis"
                )
                ui.button(
                    icon="star" if starred else "star_border",
                    on_click=lambda lid=lote["lote_id"], flag=starred: toggle(
                        lid, not flag
                    ),
                ).props(
                    "flat round dense color=amber-8" if starred else "flat round dense"
                )
            with ui.row().classes("gap-1 mt-1"):
                ui.chip(lote["condicao"] or "—", color="primary").props("dense outline")
                ui.chip(lote["status_edital"] or "—").props("dense outline")
            ui.label(lote["valor_fmt"]).classes("text-h6 text-primary mt-1")
            ui.label(
                f"{lote['municipio']} · lote {lote['numero_lote']}"
            ).classes("text-caption text-grey-7")


def run() -> None:
    """Sobe a UI em http://127.0.0.1:8080 após aplicar o schema 002."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL não configurada (veja .env.example)")

    global _engine
    _engine = create_db_engine(database_url)
    try:
        apply_schema(_engine)
    except Exception as exc:
        raise SystemExit(
            f"Não conectou no Postgres ({exc}).\n"
            "Suba o banco: docker compose up -d"
        ) from exc
    logger.info("Schema de interesse ok. Abrindo UI em http://127.0.0.1:8080")
    ui.run(
        title="Lotes DETRAN/MG",
        host="127.0.0.1",
        port=8080,
        reload=False,
        show=True,
        favicon="⭐",
    )
