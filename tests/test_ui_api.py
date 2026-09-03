"""Checks da API FastAPI (sem Postgres)."""

from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")

from detran_ui.app import filtros_from_query, lote_payload  # noqa: E402


def test_lote_payload_usa_proxy_e_serializa():
    out = lote_payload(
        {
            "lote_id": 1,
            "valor_atual": Decimal("1234.50"),
            "interesse": 1,
            "first_seen_at": datetime(2026, 1, 2, 3, 4, 5),
            "url_imagem": "https://portal/img.jpg",
        }
    )
    assert out["url_imagem"] == "/imagens/1"
    assert out["interesse"] is True
    assert out["ativo"] is True
    assert out["valor_atual"] == 1234.5
    assert out["first_seen_at"] == "2026-01-02T03:04:05"


def test_filtros_from_query_trim_modelo():
    filtros = filtros_from_query(
        marcas=["fiat"],
        modelo_contem="  ONIX  ",
        municipios=[],
        condicoes=[],
        status_edital=["Publicado"],
        valor_min=None,
        valor_max=None,
        ano_min=None,
        ano_max=None,
        somente_interesse=False,
        mostrar_inativos=False,
    )
    assert filtros.modelo_contem == "ONIX"
    assert filtros.marcas == ["fiat"]
    assert filtros.status_edital == ["Publicado"]
    assert filtros.mostrar_inativos is False


def test_lote_payload_respeita_ativo_false():
    out = lote_payload({"lote_id": 1, "ativo": False})
    assert out["ativo"] is False
