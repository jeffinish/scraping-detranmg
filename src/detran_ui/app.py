"""API FastAPI: lotes, flag de interesse, proxy da foto, estáticos do Vite."""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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
REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "ui" / "dist"

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

app = FastAPI(title="Lotes DETRAN/MG")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InteresseBody(BaseModel):
    flagged: bool


def _db() -> Engine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine não inicializada")
    return _engine


def _placeholder() -> Response:
    return Response(content=_PLACEHOLDER, media_type="image/svg+xml")


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def lote_payload(item: dict) -> dict:
    out = {key: _jsonable(value) for key, value in item.items()}
    out["url_imagem"] = f"/imagens/{item['lote_id']}"
    out["interesse"] = bool(item.get("interesse"))
    out["ativo"] = bool(item.get("ativo", True))
    return out


def filtros_from_query(
    marcas: list[str],
    modelo_contem: str,
    municipios: list[str],
    condicoes: list[str],
    status_edital: list[str],
    valor_min: float | None,
    valor_max: float | None,
    ano_min: int | None,
    ano_max: int | None,
    somente_interesse: bool,
    mostrar_inativos: bool,
) -> LoteFiltros:
    return LoteFiltros(
        marcas=marcas,
        modelo_contem=modelo_contem.strip(),
        municipios=municipios,
        condicoes=condicoes,
        status_edital=status_edital,
        valor_min=valor_min,
        valor_max=valor_max,
        ano_min=ano_min,
        ano_max=ano_max,
        somente_interesse=somente_interesse,
        mostrar_inativos=mostrar_inativos,
    )


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


@app.get("/api/opcoes")
def api_opcoes() -> dict:
    try:
        opcoes = list_opcoes(_db())
        opcoes["interesse_count"] = count_interesse(_db())
        return opcoes
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/lotes")
def api_lotes(
    marcas: Annotated[list[str] | None, Query()] = None,
    modelo_contem: str = "",
    municipios: Annotated[list[str] | None, Query()] = None,
    condicoes: Annotated[list[str] | None, Query()] = None,
    status_edital: Annotated[list[str] | None, Query()] = None,
    valor_min: float | None = None,
    valor_max: float | None = None,
    ano_min: int | None = None,
    ano_max: int | None = None,
    somente_interesse: bool = False,
    mostrar_inativos: bool = False,
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> dict:
    filtros = filtros_from_query(
        marcas=marcas or [],
        modelo_contem=modelo_contem,
        municipios=municipios or [],
        condicoes=condicoes or [],
        status_edital=status_edital or [],
        valor_min=valor_min,
        valor_max=valor_max,
        ano_min=ano_min,
        ano_max=ano_max,
        somente_interesse=somente_interesse,
        mostrar_inativos=mostrar_inativos,
    )
    try:
        lotes, total = list_lotes(_db(), filtros, page=page, page_size=page_size)
        n_flag = count_interesse(_db())
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "lotes": [lote_payload(item) for item in lotes],
        "total": total,
        "page": page,
        "page_size": page_size,
        "interesse_count": n_flag,
    }


@app.put("/api/lotes/{lote_id}/interesse")
def api_interesse(lote_id: int, body: InteresseBody) -> dict:
    try:
        set_interesse(_db(), lote_id, body.flagged)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"lote_id": lote_id, "flagged": body.flagged}


def _mount_ui() -> None:
    if not WEB_DIR.is_dir():
        logger.info("UI build ausente (%s); API-only", WEB_DIR)
        return
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="ui")
    logger.info("Servindo UI em %s", WEB_DIR)


def run() -> None:
    """Sobe a API em http://127.0.0.1:8080 após aplicar o schema 002."""
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
    _mount_ui()
    logger.info("Schema de interesse ok. API em http://127.0.0.1:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
