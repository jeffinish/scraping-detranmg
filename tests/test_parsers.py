"""Offline tests for HTML parsers (no network)."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from detran_scraper.parsers import (
    apply_lote_enriquecimento,
    compute_card_hash,
    leilao_id_from_lista_url,
    lista_lotes_path,
    parse_brl,
    parse_editais,
    parse_lote_detalhe,
    parse_lotes,
    parse_lotes_from_pages,
    parse_lotes_max_page,
    parse_pre_arrematante_id,
    parse_update_countdown,
    parse_update_single,
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


def test_parse_editais_em_andamento_status():
    editais = parse_editais(_read("home_edital_em_andamento.html"))
    assert len(editais) == 1
    assert editais[0].status == "Em Andamento"
    assert editais[0].numero_edital == "1713/2026"


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


def test_parse_lote_detalhe_from_fixture():
    detalhe = parse_lote_detalhe(_read("lote_detalhe.html"))
    assert detalhe["valor_inicial"] == Decimal("200.00")
    assert detalhe["cor"] == "VERMELHA"
    assert detalhe["ano_modelo"] == 2010
    assert detalhe["ano_fabricacao"] == 2009
    assert detalhe["combustivel"] is None


def test_parse_pre_arrematante_id_and_portal_typo():
    assert parse_pre_arrematante_id(_read("lote_detalhe.html")) == "1"
    typo = '<input id="preArrematamte" value="557068" />'
    assert parse_pre_arrematante_id(typo) == "557068"
    assert parse_pre_arrematante_id("<div></div>") is None


def test_parse_update_countdown_from_fixture():
    payload = json.loads(_read("update_countdown.json"))
    estados = parse_update_countdown(payload)
    assert set(estados) == {309489, 309493}
    assert estados[309489]["valor_atual"] == Decimal("500.00")
    assert estados[309489]["valor_incremento"] == Decimal("100.00")
    assert estados[309489]["status_lote"] == "1"


def test_parse_update_countdown_rejects_error_payload():
    assert parse_update_countdown({"error": True}) == {}
    assert parse_update_countdown(["nope"]) == {}


def test_parse_update_single_from_fixture():
    payload = json.loads(_read("update_single.json"))
    estado, lances = parse_update_single(payload, lote_id=309489, leilao_id=3387)
    assert estado is not None
    assert estado["valor_atual"] == Decimal("500.00")
    assert estado["status_lote"] == "1"
    assert len(lances) == 3
    assert lances[0].valor == Decimal("500.00")
    assert lances[0].lance_em == datetime(2026, 8, 19, 20, 35, 59)
    assert lances[0].arrematante == "xxx.xxx.xxx-xx"
    assert lances[-1].valor == Decimal("200.00")


def test_parse_update_single_skips_rows_without_valor():
    payload = {
        "valor": "100.00",
        "statusLeilao": "1",
        "ultimosLances": [{"valor": None}, {"valor": "100.00", "data_hora": "2026-08-19 10:00:00"}],
    }
    _, lances = parse_update_single(payload, lote_id=1, leilao_id=1)
    assert len(lances) == 1
    assert lances[0].valor == Decimal("100.00")


def test_apply_lote_enriquecimento_does_not_blank_existing():
    lotes = parse_lotes(_read("lote_card.html"), leilao_id=3416)
    lote = lotes[0]
    enriched = apply_lote_enriquecimento(
        lote,
        estado={"valor_atual": Decimal("500.00"), "valor_incremento": Decimal("100.00")},
        detalhe={"valor_inicial": Decimal("200.00"), "cor": "VERMELHA"},
    )
    assert enriched.valor_atual == Decimal("500.00")
    assert enriched.valor_inicial == Decimal("200.00")
    assert enriched.cor == "VERMELHA"
    assert enriched.marca_modelo == lote.marca_modelo
    unchanged = apply_lote_enriquecimento(lote, detalhe={"cor": None})
    assert unchanged.cor is None
    assert unchanged.valor_atual == lote.valor_atual
