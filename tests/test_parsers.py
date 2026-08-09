"""Offline tests for HTML parsers (no network)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from detran_scraper.parsers import (
    compute_card_hash,
    leilao_id_from_lista_url,
    lista_lotes_path,
    parse_brl,
    parse_editais,
    parse_lotes,
    parse_lotes_from_pages,
    parse_lotes_max_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_editais_from_fixture():
    editais = parse_editais(_read("home_edital_card.html"))
    assert len(editais) == 1
    edital = editais[0]
    assert edital.leilao_id == 3416
    assert edital.numero_edital == "1692/2026"
    assert edital.municipio == "Belo Horizonte"
    assert edital.patio == "Pátio Central"
    assert edital.status == "Publicado"
    assert edital.data_encerramento == datetime(2026, 8, 15, 18, 0)
    assert edital.url_detalhes.endswith("/lotes/lista-lotes/3416/2026")
    assert len(edital.raw_hash) == 64


def test_parse_lotes_from_fixture():
    lotes = parse_lotes(_read("lote_card.html"), leilao_id=3416)
    assert len(lotes) == 1
    lote = lotes[0]
    assert lote.lote_id == 312935
    assert lote.leilao_id == 3416
    assert lote.numero_lote == "1"
    assert lote.condicao == "CONSERVADO"
    assert lote.marca_modelo == "I/SHINERAY XY 50 Q 2015"
    assert lote.valor_atual == Decimal("200.00")
    assert lote.valor_inicial is None
    assert lote.url_detalhes.endswith("/lotes/detalhes/312935")


def test_parse_lotes_max_page():
    assert parse_lotes_max_page(_read("lotes_pagination.html")) == 14


def test_parse_lotes_from_pages():
    html = _read("lote_card.html")
    lotes = parse_lotes_from_pages([html, html], leilao_id=3416)
    assert len(lotes) == 2
    assert lotes[0].lote_id == lotes[1].lote_id == 312935


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("R$ 1.234,56", Decimal("1234.56")),
        ("R$\xa01.000,00", Decimal("1000.00")),
        ("invalid", None),
    ],
)
def test_parse_brl(value: str, expected: Decimal | None):
    assert parse_brl(value) == expected


def test_lista_lotes_path_and_leilao_id():
    path = "/lotes/lista-lotes/3416/2026"
    assert lista_lotes_path(path) == path
    assert leilao_id_from_lista_url(path) == 3416


def test_compute_card_hash_is_deterministic():
    html = "<div>test</div>"
    assert compute_card_hash(html) == compute_card_hash(html)
